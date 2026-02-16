from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from models.enums import InvoiceStatus


@dataclass
class InvoiceLine:
    id: Optional[int] = None
    invoice_id: Optional[int] = None
    position: int = 0
    article_id: Optional[int] = None
    beschreibung: str = ""
    menge: float = 1.0
    einzelpreis: float = 0.0
    mwst: float = 19.0
    beguenstigt_35a: bool = False
    gesamt_netto: float = 0.0

    def berechne_gesamt(self):
        self.gesamt_netto = round(self.menge * self.einzelpreis, 2)


@dataclass
class Invoice:
    id: Optional[int] = None
    supplier_id: Optional[int] = None
    customer_id: Optional[int] = None
    rechnungsnr: str = ""
    datum: Optional[date] = None
    betreff: Optional[str] = None
    objekt_weg: Optional[str] = None
    ausfuehrungsdatum: Optional[date] = None
    zeitraum: Optional[str] = None
    zahlungsziel: int = 14
    rabatt_typ: Optional[str] = None
    rabatt_wert: float = 0.0
    lohnanteil_35a: float = 0.0
    geraeteanteil_35a: float = 0.0
    dankessatz: Optional[str] = None
    hinweise: Optional[str] = None
    status: str = InvoiceStatus.ENTWURF.value
    netto: float = 0.0
    mwst_betrag: float = 0.0
    brutto: float = 0.0
    pdf_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    positionen: list[InvoiceLine] = field(default_factory=list)
