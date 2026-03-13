import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("rechnungsprogramm"))

from db.database import Database


class DatabaseMigrationTests(unittest.TestCase):
    def test_initialize_adds_bank_tables_and_invoice_paid_column(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "app.db"
            db = Database(db_path)
            db.initialize()

            conn = sqlite3.connect(db_path)
            invoice_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()
            }
            self.assertIn("bezahlt_am", invoice_columns)

            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            self.assertIn("bank_connections", tables)
            self.assertIn("bank_accounts", tables)
            self.assertIn("bank_transactions", tables)
            self.assertIn("bank_transaction_matches", tables)
            conn.close()
            db.close()

    def test_initialize_is_idempotent_for_existing_db(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "existing.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER,
                    customer_id INTEGER,
                    rechnungsnr TEXT,
                    datum DATE,
                    status TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vorname TEXT,
                    nachname TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firma TEXT
                )
                """
            )
            conn.commit()
            conn.close()

            db = Database(db_path)
            db.initialize()
            db.initialize()

            conn = sqlite3.connect(db_path)
            invoice_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()
            }
            customer_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(customers)").fetchall()
            }
            self.assertIn("bezahlt_am", invoice_columns)
            self.assertIn("notizen", customer_columns)
            conn.close()
            db.close()


if __name__ == "__main__":
    unittest.main()
