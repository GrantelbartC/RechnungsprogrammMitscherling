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
