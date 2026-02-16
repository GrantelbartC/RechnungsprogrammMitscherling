from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    id: Optional[int] = None
    bezeichnung: str = ""
    beschreibung: Optional[str] = None
    preis: float = 0.0
    mwst: float = 19.0
    beguenstigt_35a: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def brutto_preis(self) -> float:
        return self.preis * (1 + self.mwst / 100)
