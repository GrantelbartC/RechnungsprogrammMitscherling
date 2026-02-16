import os
from pathlib import Path
from datetime import date


def get_appdata_dir() -> Path:
    appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Rechnungsprogramm"


def get_db_path() -> Path:
    return get_appdata_dir() / "data.db"


def get_logos_dir() -> Path:
    path = get_appdata_dir() / "logos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_backups_dir() -> Path:
    path = get_appdata_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_rechnungen_base_dir() -> Path:
    """Gibt das Basis-Verzeichnis für Rechnungen zurück.
    Falls ein benutzerdefinierter Pfad gesetzt ist, wird dieser verwendet."""
    from PySide6.QtCore import QSettings
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    custom = settings.value("export/rechnungen_pfad", "")
    if custom and Path(custom).exists():
        base = Path(custom)
    else:
        base = Path.home() / "Documents" / "Rechnungen"
    base.mkdir(parents=True, exist_ok=True)
    return base


def set_rechnungen_base_dir(path: str):
    """Speichert den benutzerdefinierten Export-Pfad."""
    from PySide6.QtCore import QSettings
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    settings.setValue("export/rechnungen_pfad", path)


def get_monatsordner(rechnungsdatum: date | None = None) -> Path:
    d = rechnungsdatum or date.today()
    ordner_name = f"Rechnungen - {d.strftime('%m%Y')}"
    path = get_rechnungen_base_dir() / ordner_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_pdf_path(rechnungsnr: str, rechnungsdatum: date | None = None) -> Path:
    ordner = get_monatsordner(rechnungsdatum)
    return ordner / f"{rechnungsnr}.pdf"
