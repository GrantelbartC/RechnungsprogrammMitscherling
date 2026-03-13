from datetime import date


def _tagesschluessel(datum: date) -> int:
    return int(datum.strftime("%Y%m%d"))


def format_kvnr(datum: date, zaehler: int) -> str:
    return f"KV-{datum:%Y}-{datum:%m%d}-{zaehler:03d}"


def naechste_kvnr(db, datum: date | None = None) -> str:
    """Generiert die naechste KV-Nummer fuer ein Datum."""
    if datum is None:
        datum = date.today()

    tagesschluessel = _tagesschluessel(datum)

    row = db.execute(
        "SELECT letzter_zaehler FROM kv_numbers WHERE jahr = ?", (tagesschluessel,)
    ).fetchone()

    if row is None:
        neuer_zaehler = 1
        db.execute(
            "INSERT INTO kv_numbers (jahr, letzter_zaehler) VALUES (?, ?)",
            (tagesschluessel, neuer_zaehler),
        )
    else:
        neuer_zaehler = row["letzter_zaehler"] + 1
        db.execute(
            "UPDATE kv_numbers SET letzter_zaehler = ? WHERE jahr = ?",
            (neuer_zaehler, tagesschluessel),
        )

    db.commit()
    return format_kvnr(datum, neuer_zaehler)
