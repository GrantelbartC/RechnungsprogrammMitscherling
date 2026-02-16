from datetime import date
from models.invoice import Invoice, InvoiceLine
from db.database import Database


class InvoiceRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_invoice(self, row, load_lines: bool = False) -> Invoice:
        d = {k: row[k] for k in row.keys()}
        inv = Invoice(**d)
        if load_lines and inv.id:
            inv.positionen = self.get_lines(inv.id)
        return inv

    def _row_to_line(self, row) -> InvoiceLine:
        d = {k: row[k] for k in row.keys()}
        d["beguenstigt_35a"] = bool(d.get("beguenstigt_35a", 0))
        return InvoiceLine(**d)

    def get_all(self) -> list[Invoice]:
        rows = self.db.execute(
            "SELECT * FROM invoices ORDER BY datum DESC, id DESC"
        ).fetchall()
        return [self._row_to_invoice(r) for r in rows]

    def get_by_id(self, invoice_id: int) -> Invoice | None:
        row = self.db.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
        return self._row_to_invoice(row, load_lines=True) if row else None

    def search(self, query: str) -> list[Invoice]:
        q = f"%{query}%"
        rows = self.db.execute(
            """SELECT i.* FROM invoices i
               LEFT JOIN customers c ON i.customer_id = c.id
               WHERE i.rechnungsnr LIKE ? OR i.betreff LIKE ?
               OR c.vorname LIKE ? OR c.nachname LIKE ?
               ORDER BY i.datum DESC""",
            (q, q, q, q),
        ).fetchall()
        return [self._row_to_invoice(r) for r in rows]

    def get_lines(self, invoice_id: int) -> list[InvoiceLine]:
        rows = self.db.execute(
            "SELECT * FROM invoice_lines WHERE invoice_id = ? ORDER BY position",
            (invoice_id,),
        ).fetchall()
        return [self._row_to_line(r) for r in rows]

    def create(self, inv: Invoice) -> int:
        cursor = self.db.execute(
            """INSERT INTO invoices (supplier_id, customer_id, rechnungsnr, datum,
               betreff, objekt_weg, ausfuehrungsdatum, zeitraum,
               zahlungsziel, rabatt_typ, rabatt_wert, lohnanteil_35a, geraeteanteil_35a,
               dankessatz, hinweise, status, netto, mwst_betrag, brutto, pdf_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                inv.supplier_id, inv.customer_id, inv.rechnungsnr,
                inv.datum.isoformat() if inv.datum else None,
                inv.betreff, inv.objekt_weg,
                inv.ausfuehrungsdatum.isoformat() if inv.ausfuehrungsdatum else None,
                inv.zeitraum,
                inv.zahlungsziel, inv.rabatt_typ, inv.rabatt_wert,
                inv.lohnanteil_35a, inv.geraeteanteil_35a,
                inv.dankessatz, inv.hinweise, inv.status,
                inv.netto, inv.mwst_betrag, inv.brutto, inv.pdf_path,
            ),
        )
        inv_id = cursor.lastrowid
        self._save_lines(inv_id, inv.positionen)
        self.db.commit()
        return inv_id

    def update(self, inv: Invoice):
        self.db.execute(
            """UPDATE invoices SET supplier_id=?, customer_id=?, rechnungsnr=?, datum=?,
               betreff=?, objekt_weg=?, ausfuehrungsdatum=?, zeitraum=?,
               zahlungsziel=?, rabatt_typ=?, rabatt_wert=?, lohnanteil_35a=?,
               geraeteanteil_35a=?, dankessatz=?, hinweise=?, status=?,
               netto=?, mwst_betrag=?, brutto=?, pdf_path=?,
               updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                inv.supplier_id, inv.customer_id, inv.rechnungsnr,
                inv.datum.isoformat() if inv.datum else None,
                inv.betreff, inv.objekt_weg,
                inv.ausfuehrungsdatum.isoformat() if inv.ausfuehrungsdatum else None,
                inv.zeitraum,
                inv.zahlungsziel, inv.rabatt_typ, inv.rabatt_wert,
                inv.lohnanteil_35a, inv.geraeteanteil_35a,
                inv.dankessatz, inv.hinweise, inv.status,
                inv.netto, inv.mwst_betrag, inv.brutto, inv.pdf_path,
                inv.id,
            ),
        )
        self.db.execute("DELETE FROM invoice_lines WHERE invoice_id = ?", (inv.id,))
        self._save_lines(inv.id, inv.positionen)
        self.db.commit()

    def update_status(self, invoice_id: int, status: str):
        self.db.execute(
            "UPDATE invoices SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, invoice_id),
        )
        self.db.commit()

    def update_pdf_path(self, invoice_id: int, pdf_path: str):
        self.db.execute(
            "UPDATE invoices SET pdf_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (pdf_path, invoice_id),
        )
        self.db.commit()

    def delete(self, invoice_id: int):
        self.db.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        self.db.commit()

    def _save_lines(self, invoice_id: int, lines: list[InvoiceLine]):
        for line in lines:
            line.berechne_gesamt()
            self.db.execute(
                """INSERT INTO invoice_lines (invoice_id, position, article_id,
                   beschreibung, menge, einzelpreis, mwst, beguenstigt_35a, gesamt_netto)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    invoice_id, line.position, line.article_id,
                    line.beschreibung, line.menge, line.einzelpreis,
                    line.mwst, int(line.beguenstigt_35a), line.gesamt_netto,
                ),
            )
