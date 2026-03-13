from datetime import date

from models.firmenschreiben import Firmenschreiben
from db.database import Database


class FSRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_fs(self, row) -> Firmenschreiben:
        d = {k: row[k] for k in row.keys()}
        if isinstance(d.get("datum"), str):
            try:
                parts = d["datum"].split("-")
                d["datum"] = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                d["datum"] = None
        return Firmenschreiben(**d)

    def get_all(self) -> list[Firmenschreiben]:
        rows = self.db.execute(
            "SELECT * FROM firmenschreiben ORDER BY datum DESC, id DESC"
        ).fetchall()
        return [self._row_to_fs(r) for r in rows]

    def get_by_id(self, fs_id: int) -> Firmenschreiben | None:
        row = self.db.execute(
            "SELECT * FROM firmenschreiben WHERE id = ?", (fs_id,)
        ).fetchone()
        return self._row_to_fs(row) if row else None

    def search(self, query: str) -> list[Firmenschreiben]:
        q = f"%{query}%"
        rows = self.db.execute(
            """SELECT f.* FROM firmenschreiben f
               LEFT JOIN customers c ON f.customer_id = c.id
               WHERE f.fsnr LIKE ? OR f.betreff LIKE ?
               OR c.vorname LIKE ? OR c.nachname LIKE ? OR c.firma LIKE ?
               ORDER BY f.datum DESC""",
            (q, q, q, q, q),
        ).fetchall()
        return [self._row_to_fs(r) for r in rows]

    def create(self, fs: Firmenschreiben) -> int:
        cursor = self.db.execute(
            """INSERT INTO firmenschreiben
               (supplier_id, customer_id, fsnr, datum, betreff, anrede,
                brieftext, grussformel, status, pdf_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fs.supplier_id, fs.customer_id, fs.fsnr,
                fs.datum.isoformat() if fs.datum else None,
                fs.betreff, fs.anrede, fs.brieftext,
                fs.grussformel, fs.status, fs.pdf_path,
            ),
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, fs: Firmenschreiben):
        self.db.execute(
            """UPDATE firmenschreiben SET
               supplier_id=?, customer_id=?, fsnr=?, datum=?, betreff=?, anrede=?,
               brieftext=?, grussformel=?, status=?, pdf_path=?,
               updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                fs.supplier_id, fs.customer_id, fs.fsnr,
                fs.datum.isoformat() if fs.datum else None,
                fs.betreff, fs.anrede, fs.brieftext,
                fs.grussformel, fs.status, fs.pdf_path,
                fs.id,
            ),
        )
        self.db.commit()

    def update_status(self, fs_id: int, status: str):
        self.db.execute(
            "UPDATE firmenschreiben SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, fs_id),
        )
        self.db.commit()

    def update_pdf_path(self, fs_id: int, pdf_path: str):
        self.db.execute(
            "UPDATE firmenschreiben SET pdf_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (pdf_path, fs_id),
        )
        self.db.commit()

    def delete(self, fs_id: int):
        self.db.execute("DELETE FROM firmenschreiben WHERE id = ?", (fs_id,))
        self.db.commit()
