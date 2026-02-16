from models.customer import Customer
from db.database import Database


class CustomerRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_customer(self, row) -> Customer:
        return Customer(**{k: row[k] for k in row.keys()})

    def get_all(self) -> list[Customer]:
        rows = self.db.execute(
            "SELECT * FROM customers ORDER BY nachname, vorname"
        ).fetchall()
        return [self._row_to_customer(r) for r in rows]

    def get_by_id(self, customer_id: int) -> Customer | None:
        row = self.db.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        return self._row_to_customer(row) if row else None

    def search(self, query: str) -> list[Customer]:
        q = f"%{query}%"
        rows = self.db.execute(
            """SELECT * FROM customers
               WHERE vorname LIKE ? OR nachname LIKE ? OR firma LIKE ? OR ort LIKE ?
               ORDER BY nachname, vorname""",
            (q, q, q, q),
        ).fetchall()
        return [self._row_to_customer(r) for r in rows]

    def create(self, c: Customer) -> int:
        cursor = self.db.execute(
            """INSERT INTO customers (anrede, titel, vorname, nachname, firma,
               strasse, plz, ort, email, telefon)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                c.anrede, c.titel, c.vorname, c.nachname, c.firma,
                c.strasse, c.plz, c.ort, c.email, c.telefon,
            ),
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, c: Customer):
        self.db.execute(
            """UPDATE customers SET anrede=?, titel=?, vorname=?, nachname=?, firma=?,
               strasse=?, plz=?, ort=?, email=?, telefon=?,
               updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                c.anrede, c.titel, c.vorname, c.nachname, c.firma,
                c.strasse, c.plz, c.ort, c.email, c.telefon,
                c.id,
            ),
        )
        self.db.commit()

    def delete(self, customer_id: int):
        self.db.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        self.db.commit()
