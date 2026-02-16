import json
from datetime import datetime, date
from pathlib import Path

from db.database import Database
from utils.paths import get_backups_dir


def export_backup(db: Database, output_path: Path | None = None) -> Path:
    """Exportiert alle Daten als JSON-Datei."""
    if output_path is None:
        backups_dir = get_backups_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = backups_dir / f"backup_{timestamp}.json"

    data = {
        "meta": {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
        },
        "suppliers": _table_to_list(db, "suppliers"),
        "customers": _table_to_list(db, "customers"),
        "articles": _table_to_list(db, "articles"),
        "invoices": _table_to_list(db, "invoices"),
        "invoice_lines": _table_to_list(db, "invoice_lines"),
        "invoice_numbers": _table_to_list(db, "invoice_numbers"),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return output_path


def import_backup(db: Database, input_path: Path):
    """Importiert Daten aus einer JSON-Backup-Datei."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tables_order = [
        "suppliers", "customers", "articles",
        "invoice_numbers", "invoices", "invoice_lines",
    ]

    for table in tables_order:
        if table in data and data[table]:
            _import_table(db, table, data[table])

    db.commit()


def auto_backup(db: Database, max_backups: int = 10):
    """Erstellt ein automatisches Backup und behält nur die letzten N."""
    backups_dir = get_backups_dir()
    export_backup(db, backups_dir / f"auto_{datetime.now().strftime('%Y%m%d')}.json")

    # Alte Backups aufräumen
    auto_backups = sorted(backups_dir.glob("auto_*.json"), key=lambda p: p.stat().st_mtime)
    while len(auto_backups) > max_backups:
        auto_backups[0].unlink()
        auto_backups.pop(0)


def _table_to_list(db: Database, table: str) -> list[dict]:
    rows = db.execute(f"SELECT * FROM {table}").fetchall()
    return [dict(row) for row in rows]


def _import_table(db: Database, table: str, records: list[dict]):
    if not records:
        return

    for record in records:
        columns = list(record.keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)

        db.execute(
            f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})",
            tuple(record.get(c) for c in columns),
        )
