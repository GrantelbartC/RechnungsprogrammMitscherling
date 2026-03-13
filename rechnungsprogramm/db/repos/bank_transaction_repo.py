from db.database import Database
from models.banking import BankTransaction


class BankTransactionRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_transaction(self, row) -> BankTransaction:
        return BankTransaction(**{k: row[k] for k in row.keys()})

    def get_by_id(self, transaction_id: int) -> BankTransaction | None:
        row = self.db.execute(
            "SELECT * FROM bank_transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()
        return self._row_to_transaction(row) if row else None

    def get_by_entry_hash(self, entry_hash: str) -> BankTransaction | None:
        row = self.db.execute(
            "SELECT * FROM bank_transactions WHERE entry_hash = ?",
            (entry_hash,),
        ).fetchone()
        return self._row_to_transaction(row) if row else None

    def get_for_account(self, account_id: int, limit: int | None = 500) -> list[BankTransaction]:
        sql = (
            "SELECT * FROM bank_transactions WHERE account_id = ? "
            "ORDER BY COALESCE(booking_date, value_date) DESC, id DESC"
        )
        params: tuple = (account_id,)
        if limit:
            sql += " LIMIT ?"
            params = (account_id, limit)
        rows = self.db.execute(sql, params).fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def upsert(self, transaction: BankTransaction) -> tuple[BankTransaction, bool]:
        existing = self.get_by_entry_hash(transaction.entry_hash)
        if existing:
            self.db.execute(
                """UPDATE bank_transactions
                   SET account_id = ?, booking_date = ?, value_date = ?, amount = ?,
                       currency = ?, status = ?, direction = ?, counterparty_name = ?,
                       counterparty_iban = ?, counterparty_bic = ?, purpose = ?,
                       customer_reference = ?, end_to_end_reference = ?, prima_nota = ?,
                       raw_json = ?, imported_at = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    transaction.account_id,
                    transaction.booking_date.isoformat() if transaction.booking_date else None,
                    transaction.value_date.isoformat() if transaction.value_date else None,
                    transaction.amount,
                    transaction.currency,
                    transaction.status,
                    transaction.direction,
                    transaction.counterparty_name,
                    transaction.counterparty_iban,
                    transaction.counterparty_bic,
                    transaction.purpose,
                    transaction.customer_reference,
                    transaction.end_to_end_reference,
                    transaction.prima_nota,
                    transaction.raw_json,
                    existing.id,
                ),
            )
            self.db.commit()
            return self.get_by_id(existing.id), False

        cursor = self.db.execute(
            """INSERT INTO bank_transactions (
                   account_id, entry_hash, booking_date, value_date, amount, currency,
                   status, direction, counterparty_name, counterparty_iban,
                   counterparty_bic, purpose, customer_reference,
                   end_to_end_reference, prima_nota, raw_json
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                transaction.account_id,
                transaction.entry_hash,
                transaction.booking_date.isoformat() if transaction.booking_date else None,
                transaction.value_date.isoformat() if transaction.value_date else None,
                transaction.amount,
                transaction.currency,
                transaction.status,
                transaction.direction,
                transaction.counterparty_name,
                transaction.counterparty_iban,
                transaction.counterparty_bic,
                transaction.purpose,
                transaction.customer_reference,
                transaction.end_to_end_reference,
                transaction.prima_nota,
                transaction.raw_json,
            ),
        )
        self.db.commit()
        return self.get_by_id(cursor.lastrowid), True

    def upsert_many(self, transactions: list[BankTransaction]) -> tuple[list[BankTransaction], int, int]:
        persisted: list[BankTransaction] = []
        imported_count = 0
        updated_count = 0
        for transaction in transactions:
            persisted_tx, inserted = self.upsert(transaction)
            persisted.append(persisted_tx)
            if inserted:
                imported_count += 1
            else:
                updated_count += 1
        return persisted, imported_count, updated_count
