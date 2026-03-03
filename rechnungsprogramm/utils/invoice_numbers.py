from datetime import date


def _tagesschluessel(rechnungsdatum: date) -> int:
    return int(rechnungsdatum.strftime("%Y%m%d"))


def format_rechnungsnr(rechnungsdatum: date, zaehler: int) -> str:
    return f"RE-{rechnungsdatum:%Y}-{rechnungsdatum:%m%d}-{zaehler:03d}"


def parse_rechnungsnr(rechnungsnr: str) -> tuple[int, int, int] | None:
    """Parst RE-JJJJ-MMTT-NNN und gibt (jahr, mmtt, zaehler) zurueck."""
    try:
        parts = rechnungsnr.split("-")
        if len(parts) == 4 and parts[0] == "RE":
            return int(parts[1]), int(parts[2]), int(parts[3])
        if len(parts) == 3 and parts[0] == "RE":
            # Alte Nummern im Format RE-JJJJ-NNNN bleiben parsebar.
            return int(parts[1]), 0, int(parts[2])
    except (ValueError, IndexError):
        pass
    return None


def naechste_rechnungsnr(db, rechnungsdatum: date | None = None) -> str:
    """Generiert die naechste Rechnungsnummer fuer ein Rechnungsdatum."""
    if rechnungsdatum is None:
        rechnungsdatum = date.today()

    tagesschluessel = _tagesschluessel(rechnungsdatum)

    row = db.execute(
        "SELECT letzter_zaehler FROM invoice_numbers WHERE jahr = ?", (tagesschluessel,)
    ).fetchone()

    if row is None:
        neuer_zaehler = 1
        db.execute(
            "INSERT INTO invoice_numbers (jahr, letzter_zaehler) VALUES (?, ?)",
            (tagesschluessel, neuer_zaehler),
        )
    else:
        neuer_zaehler = row["letzter_zaehler"] + 1
        db.execute(
            "UPDATE invoice_numbers SET letzter_zaehler = ? WHERE jahr = ?",
            (neuer_zaehler, tagesschluessel),
        )

    db.commit()
    return format_rechnungsnr(rechnungsdatum, neuer_zaehler)
