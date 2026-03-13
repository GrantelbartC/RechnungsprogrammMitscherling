import sqlite3
from pathlib import Path

from utils.paths import get_db_path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firma TEXT NOT NULL,
    inhaber TEXT,
    strasse TEXT,
    plz TEXT,
    ort TEXT,
    postfach TEXT,
    telefon TEXT,
    telefon2 TEXT,
    mobil TEXT,
    telefax TEXT,
    email TEXT,
    web TEXT,
    steuernr TEXT,
    ustid TEXT,
    bank TEXT,
    iban TEXT,
    bic TEXT,
    glaeubiger_id TEXT,
    logo_path TEXT,
    dankessatz TEXT DEFAULT 'Vielen Dank für Ihren Auftrag!',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anrede TEXT DEFAULT '',
    titel TEXT,
    vorname TEXT DEFAULT '',
    nachname TEXT DEFAULT '',
    firma TEXT,
    strasse TEXT,
    plz TEXT,
    ort TEXT,
    email TEXT,
    telefon TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bezeichnung TEXT NOT NULL,
    beschreibung TEXT,
    preis REAL NOT NULL,
    mwst REAL NOT NULL DEFAULT 19,
    beguenstigt_35a BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    rechnungsnr TEXT UNIQUE NOT NULL,
    datum DATE NOT NULL,
    betreff TEXT,
    objekt_weg TEXT,
    ausfuehrungsdatum DATE,
    zeitraum TEXT,
    zahlungsziel INTEGER DEFAULT 14,
    rabatt_typ TEXT,
    rabatt_wert REAL DEFAULT 0,
    lohnanteil_35a REAL DEFAULT 0,
    geraeteanteil_35a REAL DEFAULT 0,
    dankessatz TEXT,
    hinweise TEXT,
    status TEXT DEFAULT 'entwurf' CHECK(status IN ('entwurf', 'versendet', 'bezahlt')),
    bezahlt_am DATE,
    netto REAL,
    mwst_betrag REAL,
    brutto REAL,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    position INTEGER,
    article_id INTEGER REFERENCES articles(id),
    beschreibung TEXT NOT NULL,
    menge REAL NOT NULL,
    einzelpreis REAL NOT NULL,
    mwst REAL NOT NULL,
    beguenstigt_35a BOOLEAN DEFAULT 0,
    gesamt_netto REAL
);

CREATE TABLE IF NOT EXISTS invoice_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jahr INTEGER UNIQUE NOT NULL,
    letzter_zaehler INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_datum ON invoices(datum);
CREATE INDEX IF NOT EXISTS idx_invoices_rechnungsnr ON invoices(rechnungsnr);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice ON invoice_lines(invoice_id);

CREATE TABLE IF NOT EXISTS bank_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL UNIQUE REFERENCES suppliers(id) ON DELETE CASCADE,
    bank_code_blz TEXT NOT NULL,
    fints_url TEXT NOT NULL,
    user_id TEXT NOT NULL,
    customer_id TEXT,
    tan_medium TEXT,
    client_state_blob BLOB,
    default_account_iban TEXT,
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id INTEGER NOT NULL REFERENCES bank_connections(id) ON DELETE CASCADE,
    iban TEXT,
    bic TEXT,
    account_number TEXT,
    subaccount TEXT,
    display_name TEXT NOT NULL,
    currency TEXT DEFAULT 'EUR',
    is_default BOOLEAN DEFAULT 0,
    current_balance REAL,
    available_balance REAL,
    balance_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(connection_id, iban, account_number, subaccount)
);

CREATE TABLE IF NOT EXISTS bank_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    entry_hash TEXT NOT NULL UNIQUE,
    booking_date DATE,
    value_date DATE,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    status TEXT NOT NULL CHECK(status IN ('booked', 'pending')),
    direction TEXT NOT NULL CHECK(direction IN ('incoming', 'outgoing')),
    counterparty_name TEXT,
    counterparty_iban TEXT,
    counterparty_bic TEXT,
    purpose TEXT,
    customer_reference TEXT,
    end_to_end_reference TEXT,
    prima_nota TEXT,
    raw_json TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bank_transaction_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_transaction_id INTEGER NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK(status IN ('suggested', 'confirmed', 'rejected')),
    score INTEGER DEFAULT 0,
    reason_text TEXT,
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bank_transaction_id, invoice_id)
);

CREATE INDEX IF NOT EXISTS idx_bank_accounts_connection ON bank_accounts(connection_id);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_default ON bank_accounts(connection_id, is_default);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_account ON bank_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_booking_date ON bank_transactions(booking_date);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_status ON bank_transactions(status);
CREATE INDEX IF NOT EXISTS idx_bank_matches_status ON bank_transaction_matches(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_matches_confirmed_tx
    ON bank_transaction_matches(bank_transaction_id) WHERE status = 'confirmed';
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_matches_confirmed_invoice
    ON bank_transaction_matches(invoice_id) WHERE status = 'confirmed';

CREATE TABLE IF NOT EXISTS kostenvoranschlaege (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    kvnr TEXT UNIQUE NOT NULL,
    datum DATE NOT NULL,
    betreff TEXT,
    objekt_weg TEXT,
    gueltig_tage INTEGER DEFAULT 30,
    rabatt_typ TEXT,
    rabatt_wert REAL DEFAULT 0,
    dankessatz TEXT,
    hinweise TEXT,
    status TEXT DEFAULT 'offen' CHECK(status IN ('offen', 'angenommen', 'abgelehnt')),
    netto REAL,
    mwst_betrag REAL,
    brutto REAL,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kv_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kv_id INTEGER NOT NULL REFERENCES kostenvoranschlaege(id) ON DELETE CASCADE,
    position INTEGER,
    article_id INTEGER REFERENCES articles(id),
    beschreibung TEXT NOT NULL,
    menge REAL NOT NULL,
    einzelpreis REAL NOT NULL,
    mwst REAL NOT NULL,
    gesamt_netto REAL
);

CREATE TABLE IF NOT EXISTS kv_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jahr INTEGER UNIQUE NOT NULL,
    letzter_zaehler INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_kv_status ON kostenvoranschlaege(status);
CREATE INDEX IF NOT EXISTS idx_kv_datum ON kostenvoranschlaege(datum);
CREATE INDEX IF NOT EXISTS idx_kv_kvnr ON kostenvoranschlaege(kvnr);
CREATE INDEX IF NOT EXISTS idx_kv_customer ON kostenvoranschlaege(customer_id);
CREATE INDEX IF NOT EXISTS idx_kv_lines_kv ON kv_lines(kv_id);

CREATE TABLE IF NOT EXISTS firmenschreiben (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER REFERENCES suppliers(id),
    customer_id INTEGER REFERENCES customers(id),
    fsnr        TEXT UNIQUE NOT NULL,
    datum       DATE NOT NULL,
    betreff     TEXT,
    anrede      TEXT,
    brieftext   TEXT,
    grussformel TEXT DEFAULT 'Mit freundlichen Grüßen',
    status      TEXT DEFAULT 'entwurf' CHECK(status IN ('entwurf', 'versendet')),
    pdf_path    TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fs_numbers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tagesschluessel INTEGER UNIQUE NOT NULL,
    letzter_zaehler INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_fs_status ON firmenschreiben(status);
CREATE INDEX IF NOT EXISTS idx_fs_datum ON firmenschreiben(datum);
CREATE INDEX IF NOT EXISTS idx_fs_fsnr ON firmenschreiben(fsnr);
"""


class Database:
    _instance = None

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None

    @classmethod
    def get_instance(cls, db_path: Path | None = None) -> "Database":
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self):
        self.connection.executescript(SCHEMA_SQL)
        self._migrate()
        self.connection.commit()

    def _migrate(self):
        """Migriert bestehende DB-Schemas auf aktuelle Version."""
        cursor = self.connection.execute("PRAGMA table_info(invoices)")
        columns = {row[1] for row in cursor.fetchall()}
        # zeitraum_von/zeitraum_bis -> zeitraum (TEXT)
        if "zeitraum_von" in columns and "zeitraum" not in columns:
            self.connection.execute("ALTER TABLE invoices ADD COLUMN zeitraum TEXT")
            self.connection.execute(
                "UPDATE invoices SET zeitraum = zeitraum_von || ' - ' || zeitraum_bis "
                "WHERE zeitraum_von IS NOT NULL AND zeitraum_bis IS NOT NULL"
            )
        if "bezahlt_am" not in columns:
            self.connection.execute("ALTER TABLE invoices ADD COLUMN bezahlt_am DATE")

        supplier_cursor = self.connection.execute("PRAGMA table_info(suppliers)")
        supplier_columns = {row[1] for row in supplier_cursor.fetchall()}
        if "glaeubiger_id" not in supplier_columns:
            self.connection.execute("ALTER TABLE suppliers ADD COLUMN glaeubiger_id TEXT")

        customer_cursor = self.connection.execute("PRAGMA table_info(customers)")
        customer_columns = {row[1] for row in customer_cursor.fetchall()}
        if "notizen" not in customer_columns:
            self.connection.execute("ALTER TABLE customers ADD COLUMN notizen TEXT")

        bank_account_cursor = self.connection.execute("PRAGMA table_info(bank_accounts)")
        bank_account_columns = {row[1] for row in bank_account_cursor.fetchall()}
        if bank_account_columns and "current_balance" not in bank_account_columns:
            self.connection.execute("ALTER TABLE bank_accounts ADD COLUMN current_balance REAL")
        if bank_account_columns and "available_balance" not in bank_account_columns:
            self.connection.execute("ALTER TABLE bank_accounts ADD COLUMN available_balance REAL")
        if bank_account_columns and "balance_date" not in bank_account_columns:
            self.connection.execute("ALTER TABLE bank_accounts ADD COLUMN balance_date DATE")

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        return self.connection.executemany(sql, params_list)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()
