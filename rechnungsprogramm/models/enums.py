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


class KVStatus(str, Enum):
    OFFEN = "offen"
    ANGENOMMEN = "angenommen"
    ABGELEHNT = "abgelehnt"


class FirmenschreibenStatus(str, Enum):
    ENTWURF = "entwurf"
    VERSENDET = "versendet"


class BankTransactionStatus(str, Enum):
    BOOKED = "booked"
    PENDING = "pending"


class BankTransactionDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class BankMatchStatus(str, Enum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
