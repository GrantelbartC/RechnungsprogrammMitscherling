from PySide6.QtCore import QSettings


def _settings() -> QSettings:
    return QSettings("Rechnungsprogramm", "Rechnungsprogramm")


def get_bank_product_id() -> str:
    return str(_settings().value("banking/product_id", "") or "").strip()


def set_bank_product_id(product_id: str):
    _settings().setValue("banking/product_id", product_id.strip())
