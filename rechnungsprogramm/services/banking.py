from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from fints.client import FinTS3PinTanClient, NeedRetryResponse, NeedTANResponse
from fints.models import SEPAAccount

from db.database import Database
from db.repos.bank_account_repo import BankAccountRepo
from db.repos.bank_connection_repo import BankConnectionRepo
from db.repos.bank_match_repo import BankMatchRepo
from db.repos.bank_transaction_repo import BankTransactionRepo
from db.repos.customer_repo import CustomerRepo
from db.repos.invoice_repo import InvoiceRepo
from db.repos.supplier_repo import SupplierRepo
from models.banking import (
    BankAccount,
    BankConnection,
    BankOperationResult,
    BankSyncResult,
    BankTransaction,
    BankTransactionMatch,
    PendingTanSession,
)
from models.customer import Customer
from models.enums import (
    BankMatchStatus,
    BankTransactionDirection,
    BankTransactionStatus,
)


class BankingServiceError(Exception):
    pass


class ProductIdMissingError(BankingServiceError):
    pass


class UnsupportedTanMethodError(BankingServiceError):
    pass


class BankingService:
    ACTION_LOAD_ACCOUNTS = "load_accounts"
    ACTION_FETCH_BALANCE = "fetch_balance"
    ACTION_FETCH_TRANSACTIONS = "fetch_transactions"

    def __init__(
        self,
        db: Database,
        client_factory: Callable[..., Any] = FinTS3PinTanClient,
    ):
        self.db = db
        self.client_factory = client_factory
        self.connection_repo = BankConnectionRepo(db)
        self.account_repo = BankAccountRepo(db)
        self.transaction_repo = BankTransactionRepo(db)
        self.match_repo = BankMatchRepo(db)
        self.invoice_repo = InvoiceRepo(db)
        self.customer_repo = CustomerRepo(db)
        self.supplier_repo = SupplierRepo(db)

    def get_connection_for_supplier(self, supplier_id: int) -> BankConnection | None:
        return self.connection_repo.get_by_supplier_id(supplier_id)

    def save_connection(self, connection: BankConnection) -> BankConnection:
        if not connection.supplier_id:
            raise BankingServiceError("Rechnungssteller fehlt.")
        if not connection.bank_code_blz.strip():
            raise BankingServiceError("BLZ ist ein Pflichtfeld.")
        if not connection.fints_url.strip():
            raise BankingServiceError("FinTS-URL ist ein Pflichtfeld.")
        if not connection.user_id.strip():
            raise BankingServiceError("Benutzerkennung ist ein Pflichtfeld.")

        existing = self.connection_repo.get_by_supplier_id(connection.supplier_id)
        if existing:
            if (
                existing.bank_code_blz != connection.bank_code_blz
                or existing.fints_url != connection.fints_url
                or existing.user_id != connection.user_id
                or (existing.customer_id or "") != (connection.customer_id or "")
                or (existing.tan_medium or "") != (connection.tan_medium or "")
            ):
                connection.client_state_blob = None
            else:
                connection.client_state_blob = existing.client_state_blob
                connection.last_sync_at = existing.last_sync_at
            connection.default_account_iban = existing.default_account_iban

        return self.connection_repo.save(connection)

    def get_accounts_for_connection(self, connection_id: int) -> list[BankAccount]:
        return self.account_repo.get_for_connection(connection_id)

    def get_default_account(self, connection_id: int) -> BankAccount | None:
        return self.account_repo.get_default_for_connection(connection_id)

    def set_default_account(self, connection_id: int, account_id: int):
        account = self.account_repo.get_by_id(account_id)
        if not account or account.connection_id != connection_id:
            raise BankingServiceError("Standardkonto konnte nicht gefunden werden.")
        self.account_repo.set_default(connection_id, account_id)
        self.connection_repo.set_default_account(connection_id, account.iban)

    def get_transactions_for_account(self, account_id: int) -> list[dict]:
        rows: list[dict] = []
        for transaction in self.transaction_repo.get_for_account(account_id):
            match = self._preferred_match(transaction.id)
            rows.append(
                {
                    "transaction": transaction,
                    "match": match,
                    "match_label": self._match_label(match.status if match else None),
                }
            )
        return rows

    def get_suggestions_for_account(self, account_id: int) -> list[dict]:
        return self.match_repo.list_suggestions_for_account(account_id)

    def fetch_accounts(self, connection_id: int, pin: str, product_id: str) -> BankOperationResult:
        connection = self._get_connection(connection_id)
        response, client_state_blob = self._run_action(
            connection,
            pin,
            product_id,
            self.ACTION_LOAD_ACCOUNTS,
            {},
            lambda client: client.get_sepa_accounts(),
        )
        if isinstance(response, PendingTanSession):
            return BankOperationResult(
                action=self.ACTION_LOAD_ACCOUNTS,
                connection_id=connection_id,
                pending_tan_session=response,
            )

        accounts = self._persist_accounts(connection, response)
        self.connection_repo.update_client_state(connection_id, client_state_blob)
        return BankOperationResult(
            action=self.ACTION_LOAD_ACCOUNTS,
            connection_id=connection_id,
            accounts=accounts,
        )

    def fetch_balance(
        self,
        connection_id: int,
        account_id: int,
        pin: str,
        product_id: str,
    ) -> BankOperationResult:
        connection = self._get_connection(connection_id)
        account = self._get_account(account_id, connection_id)

        response, client_state_blob = self._run_action(
            connection,
            pin,
            product_id,
            self.ACTION_FETCH_BALANCE,
            {"account_id": account_id},
            lambda client: client.get_balance(self._to_sepa_account(account)),
        )
        if isinstance(response, PendingTanSession):
            return BankOperationResult(
                action=self.ACTION_FETCH_BALANCE,
                connection_id=connection_id,
                pending_tan_session=response,
            )

        balance_amount, available_balance, balance_date = self._normalize_balance(response)
        self.account_repo.update_balance(account_id, balance_amount, available_balance, balance_date)
        self.connection_repo.update_client_state(connection_id, client_state_blob)
        refreshed = self._get_account(account_id, connection_id)
        return BankOperationResult(
            action=self.ACTION_FETCH_BALANCE,
            connection_id=connection_id,
            sync_result=BankSyncResult(
                account=refreshed,
                balance=balance_amount,
                available_balance=available_balance,
                balance_date=balance_date,
            ),
        )

    def fetch_transactions(
        self,
        connection_id: int,
        account_id: int,
        pin: str,
        product_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> BankOperationResult:
        connection = self._get_connection(connection_id)
        account = self._get_account(account_id, connection_id)
        resolved_start, resolved_end = self._resolve_sync_window(account_id, start_date, end_date)

        response, client_state_blob = self._run_action(
            connection,
            pin,
            product_id,
            self.ACTION_FETCH_TRANSACTIONS,
            {
                "account_id": account_id,
                "start_date": resolved_start.isoformat() if resolved_start else None,
                "end_date": resolved_end.isoformat() if resolved_end else None,
            },
            lambda client: client.get_transactions(
                self._to_sepa_account(account),
                start_date=resolved_start,
                end_date=resolved_end,
                include_pending=True,
            ),
        )
        if isinstance(response, PendingTanSession):
            return BankOperationResult(
                action=self.ACTION_FETCH_TRANSACTIONS,
                connection_id=connection_id,
                pending_tan_session=response,
            )

        transactions = self._normalize_transactions(account, response)
        persisted_transactions, imported_count, updated_count = self.transaction_repo.upsert_many(transactions)
        suggested = self._rebuild_suggestions(connection, account, persisted_transactions)
        self.connection_repo.update_client_state(connection_id, client_state_blob)
        self.connection_repo.set_last_sync(connection_id, datetime.now())
        refreshed_account = self._get_account(account_id, connection_id)
        return BankOperationResult(
            action=self.ACTION_FETCH_TRANSACTIONS,
            connection_id=connection_id,
            sync_result=BankSyncResult(
                account=refreshed_account,
                imported_count=imported_count,
                updated_count=updated_count,
                suggested_count=len(suggested),
                transactions=self.transaction_repo.get_for_account(account_id),
                suggestions=suggested,
            ),
        )

    def resume_pending_tan(
        self,
        session: PendingTanSession,
        pin: str,
        product_id: str,
        tan: str = "",
    ) -> BankOperationResult:
        connection = self._get_connection(session.connection_id)
        client = self._build_client(connection, pin, product_id, session.client_state_blob)
        challenge = NeedRetryResponse.from_data(session.challenge_blob)
        response: Any
        paused_session: PendingTanSession | None = None

        with client.resume_dialog(session.dialog_data):
            response = client.send_tan(challenge, tan)
            if isinstance(response, NeedTANResponse):
                paused_session = self._make_pending_tan_session(
                    connection=connection,
                    action=session.action,
                    payload=session.payload,
                    client=client,
                    challenge=response,
                )

        if paused_session:
            paused_session.client_state_blob = client.deconstruct()
            return BankOperationResult(
                action=session.action,
                connection_id=connection.id,
                pending_tan_session=paused_session,
            )

        client_state_blob = client.deconstruct()
        if session.action == self.ACTION_LOAD_ACCOUNTS:
            accounts = self._persist_accounts(connection, response)
            self.connection_repo.update_client_state(connection.id, client_state_blob)
            return BankOperationResult(
                action=session.action,
                connection_id=connection.id,
                accounts=accounts,
            )

        account_id = int(session.payload["account_id"])
        account = self._get_account(account_id, connection.id)

        if session.action == self.ACTION_FETCH_BALANCE:
            balance_amount, available_balance, balance_date = self._normalize_balance(response)
            self.account_repo.update_balance(account_id, balance_amount, available_balance, balance_date)
            self.connection_repo.update_client_state(connection.id, client_state_blob)
            refreshed = self._get_account(account_id, connection.id)
            return BankOperationResult(
                action=session.action,
                connection_id=connection.id,
                sync_result=BankSyncResult(
                    account=refreshed,
                    balance=balance_amount,
                    available_balance=available_balance,
                    balance_date=balance_date,
                ),
            )

        if session.action == self.ACTION_FETCH_TRANSACTIONS:
            transactions = self._normalize_transactions(account, response)
            persisted_transactions, imported_count, updated_count = self.transaction_repo.upsert_many(transactions)
            suggested = self._rebuild_suggestions(connection, account, persisted_transactions)
            self.connection_repo.update_client_state(connection.id, client_state_blob)
            self.connection_repo.set_last_sync(connection.id, datetime.now())
            refreshed = self._get_account(account_id, connection.id)
            return BankOperationResult(
                action=session.action,
                connection_id=connection.id,
                sync_result=BankSyncResult(
                    account=refreshed,
                    imported_count=imported_count,
                    updated_count=updated_count,
                    suggested_count=len(suggested),
                    transactions=self.transaction_repo.get_for_account(account_id),
                    suggestions=suggested,
                ),
            )

        raise BankingServiceError(f"Unbekannte TAN-Aktion: {session.action}")

    def confirm_match(self, transaction_id: int, invoice_id: int):
        transaction = self.transaction_repo.get_by_id(transaction_id)
        if not transaction:
            raise BankingServiceError("Umsatz nicht gefunden.")
        if self.match_repo.get_confirmed_for_transaction(transaction_id):
            raise BankingServiceError("Dieser Umsatz ist bereits bestaetigt.")
        if self.match_repo.get_confirmed_for_invoice(invoice_id):
            raise BankingServiceError("Diese Rechnung ist bereits mit einem Umsatz verknuepft.")

        self.match_repo.delete_suggestions_for_transaction(transaction_id)
        self.match_repo.save(
            BankTransactionMatch(
                bank_transaction_id=transaction_id,
                invoice_id=invoice_id,
                status=BankMatchStatus.CONFIRMED.value,
                confirmed_at=datetime.now(),
            )
        )
        paid_date = transaction.booking_date or transaction.value_date
        self.invoice_repo.mark_paid(invoice_id, paid_date)

    def reject_match(self, transaction_id: int, invoice_id: int):
        existing = self.match_repo.get_pair(transaction_id, invoice_id)
        self.match_repo.delete_suggestions_for_transaction(transaction_id)
        self.match_repo.save(
            BankTransactionMatch(
                bank_transaction_id=transaction_id,
                invoice_id=invoice_id,
                status=BankMatchStatus.REJECTED.value,
                score=existing.score if existing else 0,
                reason_text=existing.reason_text if existing else None,
            )
        )

    def _run_action(
        self,
        connection: BankConnection,
        pin: str,
        product_id: str,
        action: str,
        payload: dict[str, Any],
        func: Callable[[Any], Any],
    ) -> tuple[Any, bytes]:
        client = self._build_client(connection, pin, product_id, connection.client_state_blob)
        response: Any
        paused_session: PendingTanSession | None = None
        with client:
            response = func(client)
            if isinstance(response, NeedTANResponse):
                paused_session = self._make_pending_tan_session(
                    connection=connection,
                    action=action,
                    payload=payload,
                    client=client,
                    challenge=response,
                )
        if paused_session:
            paused_session.client_state_blob = client.deconstruct()
            return paused_session, b""
        return response, client.deconstruct()

    def _build_client(
        self,
        connection: BankConnection,
        pin: str,
        product_id: str,
        from_data: bytes | None,
    ):
        if not product_id.strip():
            raise ProductIdMissingError("Bitte zuerst eine gueltige product_id hinterlegen.")
        return self.client_factory(
            connection.bank_code_blz,
            connection.user_id,
            pin,
            connection.fints_url,
            customer_id=connection.customer_id or None,
            tan_medium=connection.tan_medium or None,
            from_data=from_data,
            product_id=product_id.strip(),
        )

    def _make_pending_tan_session(
        self,
        connection: BankConnection,
        action: str,
        payload: dict[str, Any],
        client,
        challenge: NeedTANResponse,
    ) -> PendingTanSession:
        if challenge.challenge_hhduc and not challenge.challenge_matrix:
            raise UnsupportedTanMethodError(
                "chipTAN/Flicker wird in dieser Version nicht unterstuetzt. "
                "Bitte waehlen Sie bei der Bank ein Text-, App- oder PhotoTAN-Verfahren."
            )
        dialog_data = client.pause_dialog()
        challenge_matrix_mime = None
        challenge_matrix_data = None
        if challenge.challenge_matrix:
            challenge_matrix_mime, challenge_matrix_data = challenge.challenge_matrix
        return PendingTanSession(
            connection_id=connection.id,
            action=action,
            client_state_blob=b"",
            dialog_data=dialog_data,
            challenge_blob=challenge.get_data(),
            challenge_text=challenge.challenge or None,
            challenge_html=challenge.challenge_html or None,
            decoupled=bool(challenge.decoupled),
            challenge_matrix_mime=challenge_matrix_mime,
            challenge_matrix_data=challenge_matrix_data,
            payload=payload,
        )

    def _persist_accounts(self, connection: BankConnection, accounts: list[Any]) -> list[BankAccount]:
        supplier = self.supplier_repo.get_by_id(connection.supplier_id)
        default_iban = connection.default_account_iban
        supplier_iban = self._normalize_iban(supplier.iban if supplier else None)
        fetched_accounts = []
        for account in accounts:
            iban = self._normalize_iban(getattr(account, "iban", None))
            fetched_accounts.append(
                BankAccount(
                    connection_id=connection.id,
                    iban=iban,
                    bic=getattr(account, "bic", None),
                    account_number=getattr(account, "accountnumber", None),
                    subaccount=getattr(account, "subaccount", None),
                    display_name=self._build_account_display_name(account),
                    currency="EUR",
                )
            )

        if fetched_accounts:
            iban_values = {self._normalize_iban(account.iban) for account in fetched_accounts if account.iban}
            if supplier_iban and supplier_iban in iban_values:
                default_iban = supplier_iban
            elif default_iban and self._normalize_iban(default_iban) in iban_values:
                default_iban = self._normalize_iban(default_iban)
            else:
                default_iban = fetched_accounts[0].iban

        persisted = self.account_repo.save_many(connection.id, fetched_accounts, default_iban)
        self.connection_repo.set_default_account(connection.id, default_iban)
        default_account = next((account for account in persisted if account.iban == default_iban), None)
        if default_account:
            self.account_repo.set_default(connection.id, default_account.id)
        return self.account_repo.get_for_connection(connection.id)

    def _resolve_sync_window(
        self,
        account_id: int,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date]:
        resolved_end = end_date or date.today()
        if start_date:
            return start_date, resolved_end

        latest = None
        latest_transactions = self.transaction_repo.get_for_account(account_id, limit=1)
        if latest_transactions:
            latest = latest_transactions[0].booking_date or latest_transactions[0].value_date
        if latest:
            return latest - timedelta(days=7), resolved_end
        return resolved_end - timedelta(days=180), resolved_end

    def _normalize_balance(self, balance) -> tuple[float | None, float | None, date | None]:
        amount, _ = self._extract_amount_and_currency(
            getattr(balance, "amount", None),
            getattr(balance, "status", None),
        )
        return amount, None, self._coerce_date(getattr(balance, "date", None))

    def _normalize_transactions(self, account: BankAccount, transactions: list[Any]) -> list[BankTransaction]:
        normalized: list[BankTransaction] = []
        for raw_transaction in transactions:
            data = self._transaction_data(raw_transaction)
            booking_date = self._coerce_date(data.get("date") or data.get("booking_date"))
            value_date = self._coerce_date(data.get("entry_date") or data.get("value_date"))
            amount, currency = self._extract_amount_and_currency(data.get("amount"), data.get("status"))
            if amount is None:
                continue

            status = self._infer_transaction_status(data, booking_date)
            direction = self._infer_direction(amount, data.get("status"))
            counterparty_name = self._first_text(
                data,
                "applicant_name",
                "counterparty_name",
                "name",
                "recipient_name",
                "payer_name",
            )
            purpose = self._join_texts(
                data.get("purpose"),
                data.get("purpose_lines"),
                data.get("remittance_information_unstructured"),
                data.get("description"),
            )
            customer_reference = self._first_text(
                data,
                "customer_reference",
                "reference",
                "applicant_reference",
            )
            end_to_end_reference = self._first_text(data, "end_to_end_reference", "eref")
            prima_nota = self._first_text(data, "prima_nota", "prima_nota_number")
            counterparty_iban = self._normalize_iban(
                self._first_text(data, "applicant_iban", "iban", "counterparty_iban")
            )
            counterparty_bic = self._first_text(data, "applicant_bin", "bic", "counterparty_bic")
            entry_hash = self._build_entry_hash(
                account,
                booking_date,
                value_date,
                amount,
                currency,
                counterparty_name,
                counterparty_iban,
                purpose,
                customer_reference,
                end_to_end_reference,
                prima_nota,
                status,
            )
            normalized.append(
                BankTransaction(
                    account_id=account.id,
                    entry_hash=entry_hash,
                    booking_date=booking_date,
                    value_date=value_date,
                    amount=amount,
                    currency=currency or "EUR",
                    status=status,
                    direction=direction,
                    counterparty_name=counterparty_name,
                    counterparty_iban=counterparty_iban,
                    counterparty_bic=counterparty_bic,
                    purpose=purpose,
                    customer_reference=customer_reference,
                    end_to_end_reference=end_to_end_reference,
                    prima_nota=prima_nota,
                    raw_json=json.dumps(self._json_safe(data), ensure_ascii=True, sort_keys=True),
                )
            )
        return normalized

    def _rebuild_suggestions(
        self,
        connection: BankConnection,
        account: BankAccount,
        transactions: list[BankTransaction],
    ) -> list[BankTransactionMatch]:
        if not account.is_default:
            return []

        invoices = [
            invoice
            for invoice in self.invoice_repo.get_matchable_invoices()
            if invoice.supplier_id == connection.supplier_id
        ]
        customer_cache: dict[int, Customer | None] = {}
        suggested: list[BankTransactionMatch] = []

        for transaction in transactions:
            if transaction.status != BankTransactionStatus.BOOKED.value:
                continue
            if transaction.direction != BankTransactionDirection.INCOMING.value:
                continue
            if self.match_repo.get_confirmed_for_transaction(transaction.id):
                continue

            self.match_repo.delete_suggestions_for_transaction(transaction.id)
            candidates: list[tuple[int, int, str]] = []
            for invoice in invoices:
                if self.match_repo.get_confirmed_for_invoice(invoice.id):
                    continue
                if round(abs(transaction.amount), 2) != round(invoice.brutto or 0.0, 2):
                    continue

                existing_pair = self.match_repo.get_pair(transaction.id, invoice.id)
                if existing_pair and existing_pair.status == BankMatchStatus.REJECTED.value:
                    continue

                score = 60
                reasons = ["Exakter Betrag"]
                haystack = self._match_haystack(transaction)
                if invoice.rechnungsnr and invoice.rechnungsnr.lower() in haystack:
                    score += 25
                    reasons.append("Rechnungsnummer im Verwendungszweck")

                if invoice.customer_id not in customer_cache:
                    customer_cache[invoice.customer_id] = self.customer_repo.get_by_id(invoice.customer_id)
                customer = customer_cache[invoice.customer_id]
                if customer and self._customer_matches_transaction(customer, haystack):
                    score += 10
                    reasons.append("Kundenname erkannt")

                if invoice.datum and transaction.booking_date:
                    delta_days = (transaction.booking_date - invoice.datum).days
                    if 0 <= delta_days <= 45:
                        score += 5
                        reasons.append("Zahlung im 45-Tage-Fenster")

                candidates.append((score, invoice.id, ", ".join(reasons)))

            if not candidates:
                continue

            candidates.sort(key=lambda item: item[0], reverse=True)
            top_score, top_invoice_id, top_reason = candidates[0]
            second_score = candidates[1][0] if len(candidates) > 1 else None
            if top_score < 60:
                continue
            if second_score is not None and top_score - second_score < 15:
                continue

            suggested.append(
                self.match_repo.save(
                    BankTransactionMatch(
                        bank_transaction_id=transaction.id,
                        invoice_id=top_invoice_id,
                        status=BankMatchStatus.SUGGESTED.value,
                        score=top_score,
                        reason_text=top_reason,
                    )
                )
            )
        return suggested

    def _get_connection(self, connection_id: int) -> BankConnection:
        connection = self.connection_repo.get_by_id(connection_id)
        if not connection:
            raise BankingServiceError("Bankverbindung nicht gefunden.")
        return connection

    def _get_account(self, account_id: int, connection_id: int) -> BankAccount:
        account = self.account_repo.get_by_id(account_id)
        if not account or account.connection_id != connection_id:
            raise BankingServiceError("Bankkonto nicht gefunden.")
        return account

    def _to_sepa_account(self, account: BankAccount) -> SEPAAccount:
        return SEPAAccount(
            account.iban,
            account.bic,
            account.account_number,
            account.subaccount,
            "",
        )

    def _build_account_display_name(self, account: Any) -> str:
        iban = self._normalize_iban(getattr(account, "iban", None))
        account_number = getattr(account, "accountnumber", None)
        bic = getattr(account, "bic", None)
        parts = [part for part in [iban, account_number, bic] if part]
        return " / ".join(parts) if parts else "Bankkonto"

    def _match_haystack(self, transaction: BankTransaction) -> str:
        return " ".join(
            part.lower()
            for part in [
                transaction.purpose or "",
                transaction.customer_reference or "",
                transaction.end_to_end_reference or "",
                transaction.counterparty_name or "",
            ]
            if part
        )

    def _customer_matches_transaction(self, customer: Customer, haystack: str) -> bool:
        candidates = []
        if customer.firma:
            candidates.append(customer.firma)
        if customer.vorname:
            candidates.append(customer.vorname)
        if customer.nachname:
            candidates.append(customer.nachname)
        return any(candidate.lower() in haystack for candidate in candidates if len(candidate) >= 3)

    def _preferred_match(self, transaction_id: int) -> BankTransactionMatch | None:
        matches = self.match_repo.get_for_transaction(transaction_id)
        if not matches:
            return None
        priority = {
            BankMatchStatus.CONFIRMED.value: 3,
            BankMatchStatus.SUGGESTED.value: 2,
            BankMatchStatus.REJECTED.value: 1,
        }
        matches.sort(key=lambda match: priority.get(match.status, 0), reverse=True)
        return matches[0]

    def _match_label(self, status: str | None) -> str:
        if status == BankMatchStatus.CONFIRMED.value:
            return "Bestaetigt"
        if status == BankMatchStatus.SUGGESTED.value:
            return "Vorgeschlagen"
        if status == BankMatchStatus.REJECTED.value:
            return "Abgelehnt"
        return ""

    def _transaction_data(self, transaction: Any) -> dict[str, Any]:
        if hasattr(transaction, "data") and isinstance(transaction.data, dict):
            return dict(transaction.data)
        if isinstance(transaction, dict):
            return dict(transaction)
        return {}

    def _extract_amount_and_currency(self, raw_amount: Any, raw_status: Any) -> tuple[float | None, str | None]:
        currency = None
        amount_value = raw_amount
        if hasattr(raw_amount, "amount"):
            amount_value = getattr(raw_amount, "amount")
            currency = getattr(raw_amount, "currency", None)
        elif isinstance(raw_amount, dict):
            amount_value = raw_amount.get("amount") or raw_amount.get("value")
            currency = raw_amount.get("currency")

        if amount_value is None:
            return None, currency

        try:
            amount_decimal = Decimal(str(amount_value).replace(",", "."))
        except (InvalidOperation, ValueError):
            return None, currency

        status = str(raw_status or "").upper()
        if status.startswith("D") and amount_decimal > 0:
            amount_decimal *= Decimal("-1")
        return round(float(amount_decimal), 2), currency

    def _infer_transaction_status(self, data: dict[str, Any], booking_date: date | None) -> str:
        status = str(data.get("status") or data.get("booking_status") or "").strip().lower()
        if status in {"pending", "pdng"}:
            return BankTransactionStatus.PENDING.value
        if status in {"booked", "book", "acct"}:
            return BankTransactionStatus.BOOKED.value
        if booking_date is None:
            return BankTransactionStatus.PENDING.value
        return BankTransactionStatus.BOOKED.value

    def _infer_direction(self, amount: float, raw_status: Any) -> str:
        status = str(raw_status or "").upper()
        if status.startswith("D"):
            return BankTransactionDirection.OUTGOING.value
        return (
            BankTransactionDirection.INCOMING.value
            if amount >= 0
            else BankTransactionDirection.OUTGOING.value
        )

    def _first_text(self, data: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                joined = self._join_texts(*value)
                if joined:
                    return joined
            text = str(value).strip()
            if text:
                return text
        return None

    def _join_texts(self, *values: Any) -> str | None:
        parts: list[str] = []
        for value in values:
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                nested = self._join_texts(*value)
                if nested:
                    parts.append(nested)
                continue
            text = str(value).strip()
            if text:
                parts.append(text)
        if not parts:
            return None
        return " | ".join(parts)

    def _build_entry_hash(
        self,
        account: BankAccount,
        booking_date: date | None,
        value_date: date | None,
        amount: float,
        currency: str | None,
        counterparty_name: str | None,
        counterparty_iban: str | None,
        purpose: str | None,
        customer_reference: str | None,
        end_to_end_reference: str | None,
        prima_nota: str | None,
        status: str,
    ) -> str:
        parts = [
            self._normalize_iban(account.iban) or account.account_number or "",
            booking_date.isoformat() if booking_date else "",
            value_date.isoformat() if value_date else "",
            f"{amount:.2f}",
            currency or "",
            counterparty_name or "",
            counterparty_iban or "",
            purpose or "",
            customer_reference or "",
            end_to_end_reference or "",
            prima_nota or "",
            status,
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _coerce_date(self, value: Any) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%y%m%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _normalize_iban(self, iban: str | None) -> str | None:
        if not iban:
            return None
        cleaned = "".join(str(iban).split()).upper()
        return cleaned or None

    def _json_safe(self, value: Any):
        if isinstance(value, dict):
            return {str(key): self._json_safe(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if hasattr(value, "data") and isinstance(value.data, dict):
            return self._json_safe(value.data)
        if isinstance(value, bytes):
            return value.decode("latin1", errors="ignore")
        return value
