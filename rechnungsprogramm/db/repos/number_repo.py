from datetime import date

from db.database import Database
from utils.invoice_numbers import format_rechnungsnr


class NumberRepo:
    def __init__(self, db: Database):
        self.db = db

    def naechste_nummer(self, rechnungsdatum: date | None = None) -> str:
        if rechnungsdatum is None:
            rechnungsdatum = date.today()

        tagesschluessel = int(rechnungsdatum.strftime("%Y%m%d"))
        row = self.db.execute(
            "SELECT letzter_zaehler FROM invoice_numbers WHERE jahr = ?", (tagesschluessel,)
        ).fetchone()

        if row is None:
            neuer_zaehler = 1
            self.db.execute(
                "INSERT INTO invoice_numbers (jahr, letzter_zaehler) VALUES (?, ?)",
                (tagesschluessel, neuer_zaehler),
            )
        else:
            neuer_zaehler = row["letzter_zaehler"] + 1
            self.db.execute(
                "UPDATE invoice_numbers SET letzter_zaehler = ? WHERE jahr = ?",
                (neuer_zaehler, tagesschluessel),
            )

        self.db.commit()
        return format_rechnungsnr(rechnungsdatum, neuer_zaehler)

    def aktueller_zaehler(self, rechnungsdatum: date | None = None) -> int:
        if rechnungsdatum is None:
            rechnungsdatum = date.today()

        tagesschluessel = int(rechnungsdatum.strftime("%Y%m%d"))
        row = self.db.execute(
            "SELECT letzter_zaehler FROM invoice_numbers WHERE jahr = ?", (tagesschluessel,)
        ).fetchone()
        return row["letzter_zaehler"] if row else 0

    def rechnungsnr_existiert(self, rechnungsnr: str) -> bool:
        row = self.db.execute(
            "SELECT COUNT(*) as cnt FROM invoices WHERE rechnungsnr = ?",
            (rechnungsnr,),
        ).fetchone()
        return row["cnt"] > 0
