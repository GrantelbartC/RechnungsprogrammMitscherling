from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from models.enums import FirmenschreibenStatus


@dataclass
class Firmenschreiben:
    id: Optional[int] = None
    supplier_id: Optional[int] = None
    customer_id: Optional[int] = None
    fsnr: str = ""
    datum: Optional[date] = None
    betreff: Optional[str] = None
    anrede: Optional[str] = None
    brieftext: Optional[str] = None
    grussformel: str = "Mit freundlichen Grüßen"
    status: str = FirmenschreibenStatus.ENTWURF.value
    pdf_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
