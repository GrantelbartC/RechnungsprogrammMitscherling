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


def get_kv_base_dir() -> Path:
    """Gibt das Basis-Verzeichnis für Kostenvoranschläge zurück."""
    from PySide6.QtCore import QSettings
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    custom = settings.value("export/kv_pfad", "")
    if custom and Path(custom).exists():
        base = Path(custom)
    else:
        base = Path.home() / "Documents" / "Kostenvoranschläge"
    base.mkdir(parents=True, exist_ok=True)
    return base


def set_kv_base_dir(path: str):
    """Speichert den benutzerdefinierten Export-Pfad für Kostenvoranschläge."""
    from PySide6.QtCore import QSettings
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    settings.setValue("export/kv_pfad", path)


def get_kv_monatsordner(datum: date | None = None) -> Path:
    d = datum or date.today()
    ordner_name = f"Kostenvoranschläge - {d.strftime('%m%Y')}"
    path = get_kv_base_dir() / ordner_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_kv_pdf_path(kvnr: str, datum: date | None = None) -> Path:
    ordner = get_kv_monatsordner(datum)
    return ordner / f"{kvnr}.pdf"


def get_mahnungen_base_dir() -> Path:
    """Gibt das Basis-Verzeichnis für Mahnungen zurück."""
    from PySide6.QtCore import QSettings
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    custom = settings.value("export/rechnungen_pfad", "")
    if custom and Path(custom).exists():
        base = Path(custom) / "Mahnungen"
    else:
        base = Path.home() / "Documents" / "Rechnungen" / "Mahnungen"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_fs_base_dir() -> Path:
    """Gibt das Basis-Verzeichnis für Firmenschreiben zurück."""
    from PySide6.QtCore import QSettings
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    custom = settings.value("export/fs_pfad", "")
    if custom and Path(custom).exists():
        base = Path(custom)
    else:
        base = Path.home() / "Documents" / "Firmenschreiben"
    base.mkdir(parents=True, exist_ok=True)
    return base


def set_fs_base_dir(path: str):
    """Speichert den benutzerdefinierten Export-Pfad für Firmenschreiben."""
    from PySide6.QtCore import QSettings
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    settings.setValue("export/fs_pfad", path)


def get_fs_monatsordner(datum: date | None = None) -> Path:
    d = datum or date.today()
    ordner_name = f"Firmenschreiben - {d.strftime('%m%Y')}"
    path = get_fs_base_dir() / ordner_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_fs_pdf_path(fsnr: str, datum: date | None = None) -> Path:
    ordner = get_fs_monatsordner(datum)
    return ordner / f"{fsnr}.pdf"


def get_mahnung_pdf_path(rechnungsnr: str, typ_slug: str, datum: date | None = None) -> Path:
    """Gibt den Speicherpfad für eine Mahnung zurück."""
    d = datum or date.today()
    ordner_name = f"Mahnungen - {d.strftime('%m%Y')}"
    ordner = get_mahnungen_base_dir() / ordner_name
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner / f"{rechnungsnr}_{typ_slug}.pdf"
