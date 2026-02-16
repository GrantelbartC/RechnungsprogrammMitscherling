from datetime import date


def format_rechnungsnr(jahr: int, zaehler: int) -> str:
    return f"RE-{jahr}-{zaehler:04d}"


def parse_rechnungsnr(rechnungsnr: str) -> tuple[int, int] | None:
    """Parst RE-JJJJ-NNNN und gibt (jahr, zaehler) zurück."""
    try:
        parts = rechnungsnr.split("-")
        if len(parts) == 3 and parts[0] == "RE":
            return int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        pass
    return None


def naechste_rechnungsnr(db, jahr: int | None = None) -> str:
    """Generiert die nächste Rechnungsnummer für das gegebene Jahr."""
    if jahr is None:
        jahr = date.today().year

    row = db.execute(
        "SELECT letzter_zaehler FROM invoice_numbers WHERE jahr = ?", (jahr,)
    ).fetchone()

    if row is None:
        neuer_zaehler = 1
        db.execute(
            "INSERT INTO invoice_numbers (jahr, letzter_zaehler) VALUES (?, ?)",
            (jahr, neuer_zaehler),
        )
    else:
        neuer_zaehler = row["letzter_zaehler"] + 1
        db.execute(
            "UPDATE invoice_numbers SET letzter_zaehler = ? WHERE jahr = ?",
            (neuer_zaehler, jahr),
        )

    db.commit()
    return format_rechnungsnr(jahr, neuer_zaehler)
