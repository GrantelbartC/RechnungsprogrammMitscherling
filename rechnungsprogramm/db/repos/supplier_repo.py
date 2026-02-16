from models.supplier import Supplier
from db.database import Database


class SupplierRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_supplier(self, row) -> Supplier:
        return Supplier(**{k: row[k] for k in row.keys()})

    def get_all(self) -> list[Supplier]:
        rows = self.db.execute("SELECT * FROM suppliers ORDER BY firma").fetchall()
        return [self._row_to_supplier(r) for r in rows]

    def get_by_id(self, supplier_id: int) -> Supplier | None:
        row = self.db.execute(
            "SELECT * FROM suppliers WHERE id = ?", (supplier_id,)
        ).fetchone()
        return self._row_to_supplier(row) if row else None

    def create(self, s: Supplier) -> int:
        cursor = self.db.execute(
            """INSERT INTO suppliers (firma, inhaber, strasse, plz, ort, postfach,
               telefon, telefon2, mobil, telefax, email, web,
               steuernr, ustid, bank, iban, bic, logo_path, dankessatz)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                s.firma, s.inhaber, s.strasse, s.plz, s.ort, s.postfach,
                s.telefon, s.telefon2, s.mobil, s.telefax, s.email, s.web,
                s.steuernr, s.ustid, s.bank, s.iban, s.bic, s.logo_path, s.dankessatz,
            ),
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, s: Supplier):
        self.db.execute(
            """UPDATE suppliers SET firma=?, inhaber=?, strasse=?, plz=?, ort=?,
               postfach=?, telefon=?, telefon2=?, mobil=?, telefax=?, email=?, web=?,
               steuernr=?, ustid=?, bank=?, iban=?, bic=?, logo_path=?, dankessatz=?,
               updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                s.firma, s.inhaber, s.strasse, s.plz, s.ort, s.postfach,
                s.telefon, s.telefon2, s.mobil, s.telefax, s.email, s.web,
                s.steuernr, s.ustid, s.bank, s.iban, s.bic, s.logo_path, s.dankessatz,
                s.id,
            ),
        )
        self.db.commit()

    def delete(self, supplier_id: int):
        self.db.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
        self.db.commit()
