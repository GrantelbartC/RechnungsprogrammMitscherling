import re


def validate_required(value: str | None, field_name: str) -> str | None:
    if not value or not value.strip():
        return f"{field_name} ist ein Pflichtfeld."
    return None


def validate_plz(plz: str | None) -> str | None:
    if plz and not re.match(r"^\d{5}$", plz.strip()):
        return "PLZ muss 5 Ziffern haben."
    return None


def validate_email(email: str | None) -> str | None:
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()):
        return "Ungültige E-Mail-Adresse."
    return None


def validate_iban(iban: str | None) -> str | None:
    if iban:
        cleaned = iban.replace(" ", "").upper()
        if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$", cleaned):
            return "Ungültiges IBAN-Format."
    return None


def validate_positive_number(value: float | None, field_name: str) -> str | None:
    if value is not None and value < 0:
        return f"{field_name} darf nicht negativ sein."
    return None
