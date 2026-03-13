from db.database import Database
from models.banking import BankTransactionMatch


class BankMatchRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_match(self, row) -> BankTransactionMatch:
        return BankTransactionMatch(**{k: row[k] for k in row.keys()})

    def get_for_transaction(self, transaction_id: int) -> list[BankTransactionMatch]:
        rows = self.db.execute(
            """SELECT * FROM bank_transaction_matches
               WHERE bank_transaction_id = ?
               ORDER BY created_at DESC, id DESC""",
            (transaction_id,),
        ).fetchall()
        return [self._row_to_match(row) for row in rows]

    def get_pair(self, transaction_id: int, invoice_id: int) -> BankTransactionMatch | None:
        row = self.db.execute(
            """SELECT * FROM bank_transaction_matches
               WHERE bank_transaction_id = ? AND invoice_id = ?""",
            (transaction_id, invoice_id),
        ).fetchone()
        return self._row_to_match(row) if row else None

    def get_confirmed_for_invoice(self, invoice_id: int) -> BankTransactionMatch | None:
        row = self.db.execute(
            """SELECT * FROM bank_transaction_matches
               WHERE invoice_id = ? AND status = 'confirmed'
               ORDER BY confirmed_at DESC, id DESC
               LIMIT 1""",
            (invoice_id,),
        ).fetchone()
        return self._row_to_match(row) if row else None

    def get_confirmed_for_transaction(self, transaction_id: int) -> BankTransactionMatch | None:
        row = self.db.execute(
            """SELECT * FROM bank_transaction_matches
               WHERE bank_transaction_id = ? AND status = 'confirmed'
               ORDER BY confirmed_at DESC, id DESC
               LIMIT 1""",
            (transaction_id,),
        ).fetchone()
        return self._row_to_match(row) if row else None

    def save(self, match: BankTransactionMatch) -> BankTransactionMatch:
        existing = self.get_pair(match.bank_transaction_id, match.invoice_id)
        if existing:
            self.db.execute(
                """UPDATE bank_transaction_matches
                   SET status = ?, score = ?, reason_text = ?, confirmed_at = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    match.status,
                    match.score,
                    match.reason_text,
                    match.confirmed_at,
                    existing.id,
                ),
            )
            match.id = existing.id
        else:
            cursor = self.db.execute(
                """INSERT INTO bank_transaction_matches (
                       bank_transaction_id, invoice_id, status, score, reason_text, confirmed_at
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    match.bank_transaction_id,
                    match.invoice_id,
                    match.status,
                    match.score,
                    match.reason_text,
                    match.confirmed_at,
                ),
            )
            match.id = cursor.lastrowid
        self.db.commit()
        row = self.db.execute(
            "SELECT * FROM bank_transaction_matches WHERE id = ?",
            (match.id,),
        ).fetchone()
        return self._row_to_match(row)

    def delete_suggestions_for_transaction(self, transaction_id: int):
        self.db.execute(
            """DELETE FROM bank_transaction_matches
               WHERE bank_transaction_id = ? AND status = 'suggested'""",
            (transaction_id,),
        )
        self.db.commit()

    def list_suggestions_for_account(self, account_id: int) -> list[dict]:
        rows = self.db.execute(
            """SELECT
                   m.id AS match_id,
                   m.bank_transaction_id,
                   m.invoice_id,
                   m.status,
                   m.score,
                   m.reason_text,
                   t.booking_date,
                   t.value_date,
                   t.amount,
                   t.currency,
                   t.purpose,
                   t.counterparty_name,
                   i.rechnungsnr,
                   i.datum AS invoice_date,
                   i.brutto
               FROM bank_transaction_matches m
               JOIN bank_transactions t ON t.id = m.bank_transaction_id
               JOIN invoices i ON i.id = m.invoice_id
               WHERE t.account_id = ? AND m.status = 'suggested'
               ORDER BY t.booking_date DESC, t.id DESC""",
            (account_id,),
        ).fetchall()
        return [{k: row[k] for k in row.keys()} for row in rows]
