from models.kostenvoranschlag import Kostenvoranschlag, KVLine
from db.database import Database


class KVRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_kv(self, row, load_lines: bool = False) -> Kostenvoranschlag:
        d = {k: row[k] for k in row.keys()}
        kv = Kostenvoranschlag(**d)
        if load_lines and kv.id:
            kv.positionen = self.get_lines(kv.id)
        return kv

    def _row_to_line(self, row) -> KVLine:
        d = {k: row[k] for k in row.keys()}
        return KVLine(**d)

    def get_all(self) -> list[Kostenvoranschlag]:
        rows = self.db.execute(
            "SELECT * FROM kostenvoranschlaege ORDER BY datum DESC, id DESC"
        ).fetchall()
        return [self._row_to_kv(r) for r in rows]

    def get_by_id(self, kv_id: int) -> Kostenvoranschlag | None:
        row = self.db.execute(
            "SELECT * FROM kostenvoranschlaege WHERE id = ?", (kv_id,)
        ).fetchone()
        return self._row_to_kv(row, load_lines=True) if row else None

    def search(self, query: str) -> list[Kostenvoranschlag]:
        q = f"%{query}%"
        rows = self.db.execute(
            """SELECT k.* FROM kostenvoranschlaege k
               LEFT JOIN customers c ON k.customer_id = c.id
               WHERE k.kvnr LIKE ? OR k.betreff LIKE ?
               OR c.vorname LIKE ? OR c.nachname LIKE ?
               ORDER BY k.datum DESC""",
            (q, q, q, q),
        ).fetchall()
        return [self._row_to_kv(r) for r in rows]

    def get_lines(self, kv_id: int) -> list[KVLine]:
        rows = self.db.execute(
            "SELECT * FROM kv_lines WHERE kv_id = ? ORDER BY position",
            (kv_id,),
        ).fetchall()
        return [self._row_to_line(r) for r in rows]

    def create(self, kv: Kostenvoranschlag) -> int:
        cursor = self.db.execute(
            """INSERT INTO kostenvoranschlaege (supplier_id, customer_id, kvnr, datum,
               betreff, objekt_weg, gueltig_tage, rabatt_typ, rabatt_wert,
               dankessatz, hinweise, status, netto, mwst_betrag, brutto, pdf_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                kv.supplier_id, kv.customer_id, kv.kvnr,
                kv.datum.isoformat() if kv.datum else None,
                kv.betreff, kv.objekt_weg, kv.gueltig_tage,
                kv.rabatt_typ, kv.rabatt_wert,
                kv.dankessatz, kv.hinweise, kv.status,
                kv.netto, kv.mwst_betrag, kv.brutto, kv.pdf_path,
            ),
        )
        kv_id = cursor.lastrowid
        self._save_lines(kv_id, kv.positionen)
        self.db.commit()
        return kv_id

    def update(self, kv: Kostenvoranschlag):
        self.db.execute(
            """UPDATE kostenvoranschlaege SET supplier_id=?, customer_id=?, kvnr=?, datum=?,
               betreff=?, objekt_weg=?, gueltig_tage=?, rabatt_typ=?, rabatt_wert=?,
               dankessatz=?, hinweise=?, status=?,
               netto=?, mwst_betrag=?, brutto=?, pdf_path=?,
               updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                kv.supplier_id, kv.customer_id, kv.kvnr,
                kv.datum.isoformat() if kv.datum else None,
                kv.betreff, kv.objekt_weg, kv.gueltig_tage,
                kv.rabatt_typ, kv.rabatt_wert,
                kv.dankessatz, kv.hinweise, kv.status,
                kv.netto, kv.mwst_betrag, kv.brutto, kv.pdf_path,
                kv.id,
            ),
        )
        self.db.execute("DELETE FROM kv_lines WHERE kv_id = ?", (kv.id,))
        self._save_lines(kv.id, kv.positionen)
        self.db.commit()

    def update_status(self, kv_id: int, status: str):
        self.db.execute(
            "UPDATE kostenvoranschlaege SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, kv_id),
        )
        self.db.commit()

    def update_pdf_path(self, kv_id: int, pdf_path: str):
        self.db.execute(
            "UPDATE kostenvoranschlaege SET pdf_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (pdf_path, kv_id),
        )
        self.db.commit()

    def delete(self, kv_id: int):
        self.db.execute("DELETE FROM kostenvoranschlaege WHERE id = ?", (kv_id,))
        self.db.commit()

    def _save_lines(self, kv_id: int, lines: list[KVLine]):
        for line in lines:
            line.berechne_gesamt()
            self.db.execute(
                """INSERT INTO kv_lines (kv_id, position, article_id,
                   beschreibung, menge, einzelpreis, mwst, gesamt_netto)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    kv_id, line.position, line.article_id,
                    line.beschreibung, line.menge, line.einzelpreis,
                    line.mwst, line.gesamt_netto,
                ),
            )
