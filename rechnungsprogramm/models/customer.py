from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Customer:
    id: Optional[int] = None
    anrede: str = ""
    titel: Optional[str] = None
    vorname: str = ""
    nachname: str = ""
    firma: Optional[str] = None
    strasse: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        parts = []
        if self.anrede:
            parts.append(self.anrede)
        if self.titel:
            parts.append(self.titel)
        if self.vorname:
            parts.append(self.vorname)
        if self.nachname:
            parts.append(self.nachname)
        name = " ".join(parts)
        if not name.strip() or name.strip() in ("Herr", "Frau", "Firma", "Diverse"):
            return self.firma or "Unbenannter Kunde"
        return name

    @property
    def full_name(self) -> str:
        name = f"{self.vorname} {self.nachname}".strip()
        return name if name else (self.firma or "Unbenannter Kunde")
