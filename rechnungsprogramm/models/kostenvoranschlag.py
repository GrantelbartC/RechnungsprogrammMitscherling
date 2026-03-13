from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from models.enums import KVStatus


@dataclass
class KVLine:
    id: Optional[int] = None
    kv_id: Optional[int] = None
    position: int = 0
    article_id: Optional[int] = None
    beschreibung: str = ""
    menge: float = 1.0
    einzelpreis: float = 0.0
    mwst: float = 19.0
    gesamt_netto: float = 0.0

    def berechne_gesamt(self):
        self.gesamt_netto = round(self.menge * self.einzelpreis, 2)


@dataclass
class Kostenvoranschlag:
    id: Optional[int] = None
    supplier_id: Optional[int] = None
    customer_id: Optional[int] = None
    kvnr: str = ""
    datum: Optional[date] = None
    betreff: Optional[str] = None
    objekt_weg: Optional[str] = None
    gueltig_tage: int = 30
    rabatt_typ: Optional[str] = None
    rabatt_wert: float = 0.0
    dankessatz: Optional[str] = None
    hinweise: Optional[str] = None
    status: str = KVStatus.OFFEN.value
    netto: float = 0.0
    mwst_betrag: float = 0.0
    brutto: float = 0.0
    pdf_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    positionen: list[KVLine] = field(default_factory=list)
