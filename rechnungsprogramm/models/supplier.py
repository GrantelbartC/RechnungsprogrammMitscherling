from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Supplier:
    id: Optional[int] = None
    firma: str = ""
    inhaber: Optional[str] = None
    strasse: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    postfach: Optional[str] = None
    telefon: Optional[str] = None
    telefon2: Optional[str] = None
    mobil: Optional[str] = None
    telefax: Optional[str] = None
    email: Optional[str] = None
    web: Optional[str] = None
    steuernr: Optional[str] = None
    ustid: Optional[str] = None
    bank: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    logo_path: Optional[str] = None
    dankessatz: str = "Vielen Dank für Ihren Auftrag!"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
