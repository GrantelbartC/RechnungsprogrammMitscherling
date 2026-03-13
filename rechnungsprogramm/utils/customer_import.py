"""Kunden-Import aus Tabellendokumenten (xlsx, ods, csv).

Erwartete Spalten (Reihenfolge egal, Groß/Kleinschreibung ignoriert):
  - Kunde       → Name oder Firma des Kunden
  - Adresse     → Straße, PLZ und Ort (kommagetrennt oder mehrzeilig)
  - Objekt+Tätigkeiten / Objekt / Tätigkeiten → wird als Notiz gespeichert
"""

import csv
import re
from pathlib import Path
from typing import Optional

from models.customer import Customer


# ---------------------------------------------------------------------------
# Name-Parsing
# ---------------------------------------------------------------------------

_FIRMA_KEYWORDS = [
    "GmbH", "AG", "GbR", "KG", "OHG", "e.K.", "mbH", "eG", "SE",
    "UG", "PartG", "e.V.", "KdöR",
]


def _parse_name(raw: str) -> dict:
    """Parst einen Kunden-Namen-String in Customer-Felder."""
    raw = raw.strip()
    if not raw:
        return {"anrede": "", "vorname": "", "nachname": "", "firma": None}

    # Firma-Erkennung
    for kw in _FIRMA_KEYWORDS:
        if kw.lower() in raw.lower():
            return {"anrede": "Firma", "vorname": "", "nachname": "", "firma": raw}

    # "Nachname, Vorname" Format
    if "," in raw:
        parts = raw.split(",", 1)
        return {
            "anrede": "",
            "vorname": parts[1].strip(),
            "nachname": parts[0].strip(),
            "firma": None,
        }

    # "Vorname Nachname" Format
    parts = raw.split(None, 1)
    if len(parts) == 1:
        return {"anrede": "", "vorname": "", "nachname": parts[0], "firma": None}
    return {"anrede": "", "vorname": parts[0], "nachname": parts[1], "firma": None}


# ---------------------------------------------------------------------------
# Adress-Parsing
# ---------------------------------------------------------------------------

_PLZ_RE = re.compile(r"^(\d{5})\s+(.+)$")


def _parse_address(raw: str) -> dict:
    """Parst eine Adresszeile in Straße, PLZ, Ort."""
    if not raw or not raw.strip():
        return {"strasse": None, "plz": None, "ort": None}

    raw = raw.strip()

    # Trennzeichen: Zeilenumbruch hat Vorrang vor Komma
    if "\n" in raw:
        parts = [p.strip() for p in raw.splitlines() if p.strip()]
    else:
        parts = [p.strip() for p in raw.split(",") if p.strip()]

    strasse = None
    plz = None
    ort = None

    if len(parts) >= 2:
        strasse = parts[0]
        rest = parts[1]
        m = _PLZ_RE.match(rest)
        if m:
            plz, ort = m.group(1), m.group(2)
        else:
            # PLZ könnte im dritten Teil stecken
            if len(parts) >= 3:
                m2 = _PLZ_RE.match(parts[2])
                if m2:
                    plz, ort = m2.group(1), m2.group(2)
                else:
                    ort = rest
            else:
                ort = rest
    elif len(parts) == 1:
        m = _PLZ_RE.match(parts[0])
        if m:
            plz, ort = m.group(1), m.group(2)
        else:
            strasse = parts[0]

    return {"strasse": strasse or None, "plz": plz or None, "ort": ort or None}


# ---------------------------------------------------------------------------
# Spalten-Erkennung
# ---------------------------------------------------------------------------

def _find_column(headers: list[str], *keywords: str) -> Optional[int]:
    """Gibt den ersten Spaltenindex zurück, dessen Header eines der Keywords enthält."""
    for i, h in enumerate(headers):
        h_norm = h.strip().lower()
        for kw in keywords:
            if kw.lower() in h_norm:
                return i
    return None


# ---------------------------------------------------------------------------
# Zeilen → Customer-Objekte
# ---------------------------------------------------------------------------

def parse_rows(rows: list[list]) -> list[Customer]:
    """Konvertiert Tabellenzeilen (erste Zeile = Header) in Customer-Objekte."""
    if not rows or len(rows) < 2:
        return []

    headers = [str(h) if h is not None else "" for h in rows[0]]

    col_kunde = _find_column(headers, "kunde", "name", "firma", "auftraggeber")
    col_adresse = _find_column(headers, "adresse", "anschrift", "address")
    col_objekt = _find_column(
        headers, "objekt", "tätigkeit", "tatigkeit", "tätigkeiten",
        "leistung", "beschreibung",
    )

    customers: list[Customer] = []
    for row in rows[1:]:
        # Leere Zeilen überspringen
        if not any(c for c in row if c is not None and str(c).strip()):
            continue

        def cell(idx: Optional[int]) -> str:
            if idx is None or idx >= len(row):
                return ""
            v = row[idx]
            return str(v).strip() if v is not None else ""

        name_fields = _parse_name(cell(col_kunde))
        addr_fields = _parse_address(cell(col_adresse))
        notizen_raw = cell(col_objekt) or None

        customers.append(Customer(
            anrede=name_fields["anrede"],
            vorname=name_fields["vorname"],
            nachname=name_fields["nachname"],
            firma=name_fields["firma"],
            strasse=addr_fields["strasse"],
            plz=addr_fields["plz"],
            ort=addr_fields["ort"],
            notizen=notizen_raw,
        ))

    return customers


# ---------------------------------------------------------------------------
# Datei-Lesen
# ---------------------------------------------------------------------------

def _read_xlsx(path: Path) -> list[list]:
    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl ist nicht installiert.\n"
            "Bitte ausführen: pip install openpyxl"
        )
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active
    rows = [list(row) for row in ws.iter_rows(values_only=True)]
    wb.close()
    return rows


def _read_ods(path: Path) -> list[list]:
    try:
        from odf.opendocument import load
        from odf.table import Table, TableRow, TableCell
        from odf.text import P
    except ImportError:
        raise ImportError(
            "odfpy ist nicht installiert.\n"
            "Bitte ausführen: pip install odfpy\n"
            "Oder Datei als .xlsx oder .csv speichern."
        )
    doc = load(str(path))
    sheets = doc.spreadsheet.getElementsByType(Table)
    if not sheets:
        return []
    sheet = sheets[0]
    rows: list[list] = []
    for tr in sheet.getElementsByType(TableRow):
        cells: list[str] = []
        for tc in tr.getElementsByType(TableCell):
            repeat = int(tc.getAttribute("numbercolumnsrepeated") or 1)
            ps = tc.getElementsByType(P)
            text = "".join(str(p) for p in ps) if ps else ""
            cells.extend([text] * repeat)
        # Leere Endzellen abschneiden
        while cells and not cells[-1]:
            cells.pop()
        rows.append(cells)
    # Leere Endzeilen abschneiden
    while rows and not any(rows[-1]):
        rows.pop()
    return rows


def _read_csv(path: Path) -> list[list]:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(path, newline="", encoding=enc) as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
                except csv.Error:
                    dialect = csv.excel  # Fallback: Komma-getrennt
                reader = csv.reader(f, dialect)
                return [row for row in reader]
        except (UnicodeDecodeError, Exception):
            continue
    return []


def read_file(path: Path) -> list[Customer]:
    """Liest eine Tabellendatei und gibt geparste Customer-Objekte zurück."""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        rows = _read_xlsx(path)
    elif suffix == ".ods":
        rows = _read_ods(path)
    elif suffix in (".csv", ".tsv"):
        rows = _read_csv(path)
    else:
        raise ValueError(
            f"Nicht unterstütztes Dateiformat: {suffix}\n"
            "Unterstützt: .xlsx, .ods, .csv, .tsv"
        )
    return parse_rows(rows)
