from db.database import Database
from utils.invoice_numbers import format_rechnungsnr


class NumberRepo:
    def __init__(self, db: Database):
        self.db = db

    def naechste_nummer(self, jahr: int) -> str:
        row = self.db.execute(
            "SELECT letzter_zaehler FROM invoice_numbers WHERE jahr = ?", (jahr,)
        ).fetchone()

        if row is None:
            neuer_zaehler = 1
            self.db.execute(
                "INSERT INTO invoice_numbers (jahr, letzter_zaehler) VALUES (?, ?)",
                (jahr, neuer_zaehler),
            )
        else:
            neuer_zaehler = row["letzter_zaehler"] + 1
            self.db.execute(
                "UPDATE invoice_numbers SET letzter_zaehler = ? WHERE jahr = ?",
                (neuer_zaehler, jahr),
            )

        self.db.commit()
        return format_rechnungsnr(jahr, neuer_zaehler)

    def aktueller_zaehler(self, jahr: int) -> int:
        row = self.db.execute(
            "SELECT letzter_zaehler FROM invoice_numbers WHERE jahr = ?", (jahr,)
        ).fetchone()
        return row["letzter_zaehler"] if row else 0

    def rechnungsnr_existiert(self, rechnungsnr: str) -> bool:
        row = self.db.execute(
            "SELECT COUNT(*) as cnt FROM invoices WHERE rechnungsnr = ?",
            (rechnungsnr,),
        ).fetchone()
        return row["cnt"] > 0
