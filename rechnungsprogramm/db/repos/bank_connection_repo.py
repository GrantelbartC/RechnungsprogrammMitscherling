from db.database import Database
from models.banking import BankConnection


class BankConnectionRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_connection(self, row) -> BankConnection:
        return BankConnection(**{k: row[k] for k in row.keys()})

    def get_all(self) -> list[BankConnection]:
        rows = self.db.execute(
            "SELECT * FROM bank_connections ORDER BY supplier_id"
        ).fetchall()
        return [self._row_to_connection(row) for row in rows]

    def get_by_id(self, connection_id: int) -> BankConnection | None:
        row = self.db.execute(
            "SELECT * FROM bank_connections WHERE id = ?",
            (connection_id,),
        ).fetchone()
        return self._row_to_connection(row) if row else None

    def get_by_supplier_id(self, supplier_id: int) -> BankConnection | None:
        row = self.db.execute(
            "SELECT * FROM bank_connections WHERE supplier_id = ?",
            (supplier_id,),
        ).fetchone()
        return self._row_to_connection(row) if row else None

    def create(self, connection: BankConnection) -> int:
        cursor = self.db.execute(
            """INSERT INTO bank_connections (
                   supplier_id, bank_code_blz, fints_url, user_id, customer_id,
                   tan_medium, client_state_blob, default_account_iban, last_sync_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                connection.supplier_id,
                connection.bank_code_blz,
                connection.fints_url,
                connection.user_id,
                connection.customer_id,
                connection.tan_medium,
                connection.client_state_blob,
                connection.default_account_iban,
                connection.last_sync_at,
            ),
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, connection: BankConnection):
        self.db.execute(
            """UPDATE bank_connections
               SET supplier_id = ?, bank_code_blz = ?, fints_url = ?, user_id = ?,
                   customer_id = ?, tan_medium = ?, client_state_blob = ?,
                   default_account_iban = ?, last_sync_at = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                connection.supplier_id,
                connection.bank_code_blz,
                connection.fints_url,
                connection.user_id,
                connection.customer_id,
                connection.tan_medium,
                connection.client_state_blob,
                connection.default_account_iban,
                connection.last_sync_at,
                connection.id,
            ),
        )
        self.db.commit()

    def save(self, connection: BankConnection) -> BankConnection:
        existing = None
        if connection.id:
            existing = self.get_by_id(connection.id)
        elif connection.supplier_id:
            existing = self.get_by_supplier_id(connection.supplier_id)
        if existing:
            connection.id = existing.id
            self.update(connection)
        else:
            connection.id = self.create(connection)
        return self.get_by_id(connection.id)

    def update_client_state(self, connection_id: int, client_state_blob: bytes | None):
        self.db.execute(
            """UPDATE bank_connections
               SET client_state_blob = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (client_state_blob, connection_id),
        )
        self.db.commit()

    def set_default_account(self, connection_id: int, iban: str | None):
        self.db.execute(
            """UPDATE bank_connections
               SET default_account_iban = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (iban, connection_id),
        )
        self.db.commit()

    def set_last_sync(self, connection_id: int, last_sync_at):
        self.db.execute(
            """UPDATE bank_connections
               SET last_sync_at = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (last_sync_at, connection_id),
        )
        self.db.commit()
