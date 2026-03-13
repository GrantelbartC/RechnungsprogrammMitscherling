from db.database import Database
from models.banking import BankAccount


class BankAccountRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_account(self, row) -> BankAccount:
        data = {k: row[k] for k in row.keys()}
        data["is_default"] = bool(data.get("is_default", 0))
        return BankAccount(**data)

    def get_by_id(self, account_id: int) -> BankAccount | None:
        row = self.db.execute(
            "SELECT * FROM bank_accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        return self._row_to_account(row) if row else None

    def get_for_connection(self, connection_id: int) -> list[BankAccount]:
        rows = self.db.execute(
            """SELECT * FROM bank_accounts
               WHERE connection_id = ?
               ORDER BY is_default DESC, display_name, iban""",
            (connection_id,),
        ).fetchall()
        return [self._row_to_account(row) for row in rows]

    def get_default_for_connection(self, connection_id: int) -> BankAccount | None:
        row = self.db.execute(
            """SELECT * FROM bank_accounts
               WHERE connection_id = ? AND is_default = 1
               ORDER BY id DESC LIMIT 1""",
            (connection_id,),
        ).fetchone()
        return self._row_to_account(row) if row else None

    def _find_existing_id(self, account: BankAccount) -> int | None:
        row = self.db.execute(
            """SELECT id FROM bank_accounts
               WHERE connection_id = ?
                 AND COALESCE(iban, '') = ?
                 AND COALESCE(account_number, '') = ?
                 AND COALESCE(subaccount, '') = ?""",
            (
                account.connection_id,
                account.iban or "",
                account.account_number or "",
                account.subaccount or "",
            ),
        ).fetchone()
        return row["id"] if row else None

    def save(self, account: BankAccount) -> BankAccount:
        existing_id = account.id or self._find_existing_id(account)
        if existing_id:
            existing = self.get_by_id(existing_id)
            self.db.execute(
                """UPDATE bank_accounts
                   SET iban = ?, bic = ?, account_number = ?, subaccount = ?,
                       display_name = ?, currency = ?, is_default = ?,
                       current_balance = ?, available_balance = ?, balance_date = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    account.iban,
                    account.bic,
                    account.account_number,
                    account.subaccount,
                    account.display_name,
                    account.currency,
                    int(account.is_default),
                    account.current_balance if account.current_balance is not None else existing.current_balance,
                    account.available_balance if account.available_balance is not None else existing.available_balance,
                    (
                        account.balance_date.isoformat()
                        if account.balance_date
                        else (
                            existing.balance_date.isoformat()
                            if existing and existing.balance_date
                            else None
                        )
                    ),
                    existing_id,
                ),
            )
            account.id = existing_id
        else:
            cursor = self.db.execute(
                """INSERT INTO bank_accounts (
                       connection_id, iban, bic, account_number, subaccount,
                       display_name, currency, is_default, current_balance,
                       available_balance, balance_date
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    account.connection_id,
                    account.iban,
                    account.bic,
                    account.account_number,
                    account.subaccount,
                    account.display_name,
                    account.currency,
                    int(account.is_default),
                    account.current_balance,
                    account.available_balance,
                    account.balance_date.isoformat() if account.balance_date else None,
                ),
            )
            account.id = cursor.lastrowid
        self.db.commit()
        return self.get_by_id(account.id)

    def save_many(
        self,
        connection_id: int,
        accounts: list[BankAccount],
        default_iban: str | None,
    ) -> list[BankAccount]:
        for account in accounts:
            account.connection_id = connection_id
            account.is_default = bool(default_iban and account.iban == default_iban)
            self.save(account)
        return self.get_for_connection(connection_id)

    def set_default(self, connection_id: int, account_id: int):
        self.db.execute(
            "UPDATE bank_accounts SET is_default = 0, updated_at = CURRENT_TIMESTAMP WHERE connection_id = ?",
            (connection_id,),
        )
        self.db.execute(
            "UPDATE bank_accounts SET is_default = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (account_id,),
        )
        self.db.commit()

    def update_balance(
        self,
        account_id: int,
        current_balance: float | None,
        available_balance: float | None,
        balance_date,
    ):
        self.db.execute(
            """UPDATE bank_accounts
               SET current_balance = ?, available_balance = ?, balance_date = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                current_balance,
                available_balance,
                balance_date.isoformat() if balance_date else None,
                account_id,
            ),
        )
        self.db.commit()
