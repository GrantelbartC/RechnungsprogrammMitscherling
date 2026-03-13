from datetime import date


def _tagesschluessel(datum: date) -> int:
    return int(datum.strftime("%Y%m%d"))


def format_fsnr(datum: date, zaehler: int) -> str:
    return f"FS-{datum:%Y}-{datum:%m%d}-{zaehler:03d}"


def naechste_fsnr(db, datum: date | None = None) -> str:
    """Generiert die naechste Firmenschreiben-Nummer fuer ein Datum."""
    if datum is None:
        datum = date.today()

    tagesschluessel = _tagesschluessel(datum)

    row = db.execute(
        "SELECT letzter_zaehler FROM fs_numbers WHERE tagesschluessel = ?", (tagesschluessel,)
    ).fetchone()

    if row is None:
        neuer_zaehler = 1
        db.execute(
            "INSERT INTO fs_numbers (tagesschluessel, letzter_zaehler) VALUES (?, ?)",
            (tagesschluessel, neuer_zaehler),
        )
    else:
        neuer_zaehler = row["letzter_zaehler"] + 1
        db.execute(
            "UPDATE fs_numbers SET letzter_zaehler = ? WHERE tagesschluessel = ?",
            (neuer_zaehler, tagesschluessel),
        )

    db.commit()
    return format_fsnr(datum, neuer_zaehler)
