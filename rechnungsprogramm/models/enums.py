from enum import Enum


class InvoiceStatus(str, Enum):
    ENTWURF = "entwurf"
    VERSENDET = "versendet"
    BEZAHLT = "bezahlt"


class RabattTyp(str, Enum):
    PROZENT = "prozent"
    BETRAG = "betrag"


class MwstSatz(float, Enum):
    NULL = 0.0
    ERMAESSIGT = 7.0
    VOLL = 19.0
