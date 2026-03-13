from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional


@dataclass
class BankConnection:
    id: Optional[int] = None
    supplier_id: Optional[int] = None
    bank_code_blz: str = ""
    fints_url: str = ""
    user_id: str = ""
    customer_id: Optional[str] = None
    tan_medium: Optional[str] = None
    client_state_blob: Optional[bytes] = None
    default_account_iban: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BankAccount:
    id: Optional[int] = None
    connection_id: Optional[int] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    account_number: Optional[str] = None
    subaccount: Optional[str] = None
    display_name: str = ""
    currency: str = "EUR"
    is_default: bool = False
    current_balance: Optional[float] = None
    available_balance: Optional[float] = None
    balance_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BankTransaction:
    id: Optional[int] = None
    account_id: Optional[int] = None
    entry_hash: str = ""
    booking_date: Optional[date] = None
    value_date: Optional[date] = None
    amount: float = 0.0
    currency: str = "EUR"
    status: str = "booked"
    direction: str = "incoming"
    counterparty_name: Optional[str] = None
    counterparty_iban: Optional[str] = None
    counterparty_bic: Optional[str] = None
    purpose: Optional[str] = None
    customer_reference: Optional[str] = None
    end_to_end_reference: Optional[str] = None
    prima_nota: Optional[str] = None
    raw_json: Optional[str] = None
    imported_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BankTransactionMatch:
    id: Optional[int] = None
    bank_transaction_id: Optional[int] = None
    invoice_id: Optional[int] = None
    status: str = "suggested"
    score: int = 0
    reason_text: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PendingTanSession:
    connection_id: int
    action: str
    client_state_blob: bytes
    dialog_data: bytes
    challenge_blob: bytes
    challenge_text: Optional[str] = None
    challenge_html: Optional[str] = None
    decoupled: bool = False
    challenge_matrix_mime: Optional[str] = None
    challenge_matrix_data: Optional[bytes] = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class BankSyncResult:
    account: BankAccount
    balance: Optional[float] = None
    balance_date: Optional[date] = None
    available_balance: Optional[float] = None
    imported_count: int = 0
    updated_count: int = 0
    suggested_count: int = 0
    transactions: list[BankTransaction] = field(default_factory=list)
    suggestions: list[BankTransactionMatch] = field(default_factory=list)


@dataclass
class BankOperationResult:
    action: str
    connection_id: int
    pending_tan_session: Optional[PendingTanSession] = None
    accounts: list[BankAccount] = field(default_factory=list)
    sync_result: Optional[BankSyncResult] = None
