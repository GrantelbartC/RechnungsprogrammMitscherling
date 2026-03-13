import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("rechnungsprogramm"))

from db.database import Database
from db.repos.bank_account_repo import BankAccountRepo
from db.repos.bank_connection_repo import BankConnectionRepo
from db.repos.customer_repo import CustomerRepo
from db.repos.invoice_repo import InvoiceRepo
from db.repos.supplier_repo import SupplierRepo
from fints.models import SEPAAccount
from models.banking import BankAccount, BankConnection, BankTransactionMatch
from models.customer import Customer
from models.enums import BankMatchStatus, InvoiceStatus
from models.invoice import Invoice
from models.supplier import Supplier
from services.banking import BankingService


class ResumeDialogContext:
    def __init__(self, client):
        self.client = client

    def __enter__(self):
        return self.client

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeChallenge:
    def __init__(self, challenge="Bitte TAN eingeben", decoupled=False):
        self.challenge = challenge
        self.challenge_html = challenge
        self.challenge_hhduc = None
        self.challenge_matrix = None
        self.decoupled = decoupled

    def get_data(self):
        return b"challenge"


class FakeClient:
    accounts_response = []
    balance_response = None
    transactions_response = []
    send_tan_response = None
    instances = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.sent_tan = None
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def resume_dialog(self, _dialog_data):
        return ResumeDialogContext(self)

    def get_sepa_accounts(self):
        return self.__class__.accounts_response

    def get_balance(self, _account):
        return self.__class__.balance_response

    def get_transactions(self, _account, start_date=None, end_date=None, include_pending=False):
        self.last_range = (start_date, end_date, include_pending)
        return self.__class__.transactions_response

    def pause_dialog(self):
        return b"dialog"

    def deconstruct(self):
        return b"client-state"

    def send_tan(self, _challenge, tan):
        self.sent_tan = tan
        return self.__class__.send_tan_response


class BankingServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.db")
        self.db.initialize()
        FakeClient.accounts_response = []
        FakeClient.balance_response = None
        FakeClient.transactions_response = []
        FakeClient.send_tan_response = None
        self.supplier_repo = SupplierRepo(self.db)
        self.customer_repo = CustomerRepo(self.db)
        self.invoice_repo = InvoiceRepo(self.db)
        self.connection_repo = BankConnectionRepo(self.db)
        self.account_repo = BankAccountRepo(self.db)

        self.supplier_id = self.supplier_repo.create(
            Supplier(firma="Mitscherling GmbH", iban="DE02120300000000202051")
        )
        self.customer_id = self.customer_repo.create(
            Customer(vorname="Max", nachname="Muster", firma="Muster GmbH")
        )
        self.service = BankingService(self.db, client_factory=FakeClient)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()
        FakeClient.instances.clear()

    def _create_connection(self) -> BankConnection:
        return self.connection_repo.save(
            BankConnection(
                supplier_id=self.supplier_id,
                bank_code_blz="12030000",
                fints_url="https://bank.example/fints",
                user_id="user1",
            )
        )

    def _create_invoice(self, number: str, amount: float, invoice_date: date, customer_id=None) -> Invoice:
        invoice = Invoice(
            supplier_id=self.supplier_id,
            customer_id=customer_id or self.customer_id,
            rechnungsnr=number,
            datum=invoice_date,
            brutto=amount,
            netto=amount,
            status=InvoiceStatus.VERSENDET.value,
        )
        invoice.id = self.invoice_repo.create(invoice)
        return invoice

    def test_fetch_accounts_persists_accounts_and_sets_default_from_supplier_iban(self):
        connection = self._create_connection()
        FakeClient.accounts_response = [
            SEPAAccount("DE02120300000000202051", "BYLADEM1001", "1234", "00", "12030000"),
            SEPAAccount("DE99120300000000202052", "BYLADEM1001", "5678", "00", "12030000"),
        ]

        result = self.service.fetch_accounts(connection.id, "12345", "product-123")

        self.assertEqual(2, len(result.accounts))
        default_account = self.service.get_default_account(connection.id)
        self.assertEqual("DE02120300000000202051", default_account.iban)

    def test_normalize_transactions_handles_mt940_and_xml_like_payloads(self):
        connection = self._create_connection()
        account = self.account_repo.save(
            BankAccount(
                connection_id=connection.id,
                iban="DE02120300000000202051",
                bic="BYLADEM1001",
                account_number="1234",
                subaccount="00",
                display_name="Testkonto",
                is_default=True,
            )
        )

        xml_tx = SimpleNamespace(
            data={
                "amount": {"amount": "100.00", "currency": "EUR"},
                "date": "2026-03-01",
                "purpose": "RE-1001",
                "applicant_name": "Muster GmbH",
            }
        )
        mt940_tx = SimpleNamespace(
            data={
                "amount": {"amount": "50.00", "currency": "EUR"},
                "status": "D",
                "entry_date": "2026-03-02",
                "purpose": ["Abbuchung"],
                "applicant_name": "Versorger AG",
            }
        )

        normalized = self.service._normalize_transactions(account, [xml_tx, mt940_tx])

        self.assertEqual(2, len(normalized))
        self.assertEqual("incoming", normalized[0].direction)
        self.assertEqual("outgoing", normalized[1].direction)
        self.assertNotEqual(normalized[0].entry_hash, normalized[1].entry_hash)

    def test_matching_suggests_single_exact_match(self):
        connection = self._create_connection()
        account = self.account_repo.save(
            BankAccount(
                connection_id=connection.id,
                iban="DE02120300000000202051",
                bic="BYLADEM1001",
                account_number="1234",
                subaccount="00",
                display_name="Testkonto",
                is_default=True,
            )
        )
        invoice = self._create_invoice("RE-1001", 100.0, date(2026, 2, 20))
        transaction = self.service._normalize_transactions(
            account,
            [
                SimpleNamespace(
                    data={
                        "amount": {"amount": "100.00", "currency": "EUR"},
                        "date": "2026-03-01",
                        "purpose": "Zahlung RE-1001",
                        "applicant_name": "Muster GmbH",
                    }
                )
            ],
        )[0]
        transaction = self.service.transaction_repo.upsert(transaction)[0]

        suggestions = self.service._rebuild_suggestions(connection, account, [transaction])

        self.assertEqual(1, len(suggestions))
        self.assertEqual(invoice.id, suggestions[0].invoice_id)
        self.assertEqual(BankMatchStatus.SUGGESTED.value, suggestions[0].status)

    def test_matching_skips_ambiguous_same_amount(self):
        connection = self._create_connection()
        account = self.account_repo.save(
            BankAccount(
                connection_id=connection.id,
                iban="DE02120300000000202051",
                bic="BYLADEM1001",
                account_number="1234",
                subaccount="00",
                display_name="Testkonto",
                is_default=True,
            )
        )
        self._create_invoice("RE-1001", 100.0, date(2026, 2, 20))
        self._create_invoice("RE-1002", 100.0, date(2026, 2, 22), customer_id=self.customer_id)
        transaction = self.service._normalize_transactions(
            account,
            [
                SimpleNamespace(
                    data={
                        "amount": {"amount": "100.00", "currency": "EUR"},
                        "date": "2026-03-05",
                        "purpose": "Zahlung",
                        "applicant_name": "Unklar",
                    }
                )
            ],
        )[0]
        transaction = self.service.transaction_repo.upsert(transaction)[0]

        suggestions = self.service._rebuild_suggestions(connection, account, [transaction])

        self.assertEqual([], suggestions)

    def test_matching_ignores_pending_and_rejected_pairs(self):
        connection = self._create_connection()
        account = self.account_repo.save(
            BankAccount(
                connection_id=connection.id,
                iban="DE02120300000000202051",
                bic="BYLADEM1001",
                account_number="1234",
                subaccount="00",
                display_name="Testkonto",
                is_default=True,
            )
        )
        invoice = self._create_invoice("RE-1001", 100.0, date(2026, 2, 20))
        pending_tx = self.service._normalize_transactions(
            account,
            [
                SimpleNamespace(
                    data={
                        "amount": {"amount": "100.00", "currency": "EUR"},
                        "status": "pending",
                        "purpose": "RE-1001",
                    }
                )
            ],
        )[0]
        pending_tx = self.service.transaction_repo.upsert(pending_tx)[0]
        self.assertEqual([], self.service._rebuild_suggestions(connection, account, [pending_tx]))

        booked_tx = self.service._normalize_transactions(
            account,
            [
                SimpleNamespace(
                    data={
                        "amount": {"amount": "100.00", "currency": "EUR"},
                        "date": "2026-03-10",
                        "purpose": "RE-1001",
                    }
                )
            ],
        )[0]
        booked_tx = self.service.transaction_repo.upsert(booked_tx)[0]
        self.service.match_repo.save(
            BankTransactionMatch(
                bank_transaction_id=booked_tx.id,
                invoice_id=invoice.id,
                status=BankMatchStatus.REJECTED.value,
                score=60,
                reason_text="Exakter Betrag",
            )
        )
        self.assertEqual([], self.service._rebuild_suggestions(connection, account, [booked_tx]))

    def test_resume_pending_tan_finishes_transaction_sync(self):
        connection = self._create_connection()
        account = self.account_repo.save(
            BankAccount(
                connection_id=connection.id,
                iban="DE02120300000000202051",
                bic="BYLADEM1001",
                account_number="1234",
                subaccount="00",
                display_name="Testkonto",
                is_default=True,
            )
        )
        self._create_invoice("RE-2001", 42.0, date(2026, 2, 25))
        challenge = FakeChallenge()
        FakeClient.transactions_response = challenge
        FakeClient.send_tan_response = [
            SimpleNamespace(
                data={
                    "amount": {"amount": "42.00", "currency": "EUR"},
                    "date": "2026-03-12",
                    "purpose": "RE-2001",
                    "applicant_name": "Muster GmbH",
                }
            )
        ]

        with patch("services.banking.NeedTANResponse", FakeChallenge):
            initial = self.service.fetch_transactions(connection.id, account.id, "12345", "product-123")
        self.assertIsNotNone(initial.pending_tan_session)

        with patch("services.banking.NeedRetryResponse.from_data", return_value=challenge):
            resumed = self.service.resume_pending_tan(
                initial.pending_tan_session,
                "12345",
                "product-123",
                "654321",
            )

        self.assertIsNotNone(resumed.sync_result)
        self.assertEqual(1, resumed.sync_result.imported_count)
        self.assertEqual(1, resumed.sync_result.suggested_count)
        self.assertEqual("654321", FakeClient.instances[-1].sent_tan)


if __name__ == "__main__":
    unittest.main()
