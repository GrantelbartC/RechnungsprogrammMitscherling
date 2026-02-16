# PRD: Rechnungsprogramm

> Desktop-Anwendung für Handwerker & Einzelunternehmer  
> Version 1.0 | Februar 2026 | Plattform: Windows | Technologie: Python + PySide6

---

## 1. Executive Summary

Das Rechnungsprogramm ist eine native Windows-Desktop-Anwendung für Handwerker und Einzelunternehmer. Es ermöglicht die Verwaltung von Rechnungsstellern, Kunden und Artikeln sowie die Erstellung professioneller Rechnungen mit PDF- und ZUGFeRD-Export (EN16931 / COMFORT-Profil).

Die Anwendung speichert alle Daten lokal in einer SQLite-Datenbank, unterstützt JSON-Import/Export für Backups, automatische Rechnungsnummern-Vergabe und eine vollständige Rechnungshistorie mit Status-Tracking.

---

## 2. Zielgruppe & Anwendungskontext

**Primäre Nutzer:** Handwerker und Einzelunternehmer (Garten-/Landschaftsbau, Hausmeisterservice, Reinigung, Renovierung etc.)

### Typische Nutzungsszenarien

- Rechnung an Privatkunden für erbrachte Handwerkerleistungen erstellen
- Rechnungen für WEG-Verwaltungen mit Objektzuordnung generieren
- Begünstigte Anteile nach §35a EStG korrekt ausweisen
- E-Rechnungen im ZUGFeRD-Format an Geschäftskunden senden
- Monatliche Rechnungsübersicht und Status-Tracking pflegen

---

## 3. Technologie-Stack

| Komponente | Technologie | Begründung |
|---|---|---|
| Framework | Python 3.11+ / PySide6 (Qt 6) | Nativ, robust, gut dokumentiert |
| UI-Engine | PySide6 Widgets + QSS Styling | Native Windows-Performance, flexible Gestaltung |
| Datenbank | SQLite 3 (via `sqlite3` stdlib) | Lokal, zero-config, bewährt, leicht backupbar |
| PDF-Erzeugung | ReportLab + Pillow | Professionelles PDF-Layout mit Logos |
| ZUGFeRD/XML | lxml + Factur-X Library | EN16931/COMFORT, standardkonforme XML-Einbettung |
| Backup | JSON-Export/Import (`json` stdlib) | Menschenlesbar, einfach übertragbar |
| Installer | PyInstaller + Inno Setup | Einzelne .exe, Windows-Installer |
| Rechnungsnummern | RE-JJJJ-NNNN (fortlaufend/Jahr) | Automatisch, konfigurierbar |

---

## 4. Systemarchitektur

### 4.1 Verzeichnisstruktur

| Pfad | Inhalt |
|---|---|
| `%APPDATA%\Rechnungsprogramm\data.db` | SQLite-Datenbank (alle Stamm- + Rechnungsdaten) |
| `%APPDATA%\Rechnungsprogramm\logos\` | Gespeicherte Firmenlogos (PNG/JPG) |
| `%APPDATA%\Rechnungsprogramm\backups\` | Automatische + manuelle JSON-Backups |
| `%USERPROFILE%\Dokumente\Rechnungen\` | Stammverzeichnis für exportierte PDFs |
| `  └─ Rechnungen - MMJJJJ\` | Monatsordner (z.B. "Rechnungen - 022026") |

### 4.2 Schichtenarchitektur

- **Präsentationsschicht (UI):** PySide6 Widgets, QSS-Theming, Tab-basierte Navigation
- **Geschäftslogik:** Python-Klassen für Berechnungen, Validierung, Nummernvergabe
- **Datenzugriffsschicht (DAL):** Repository-Pattern mit SQLite, CRUD-Operationen
- **Export-Schicht:** PDF-Generator (ReportLab), ZUGFeRD-XML-Generator (lxml/Factur-X)
- **Backup-Schicht:** JSON-Serialisierung aller Tabellen, Import mit Konflikterkennung

### 4.3 Modulstruktur

```
rechnungsprogramm/
├── main.py                     # App-Start, Fenster-Setup, Tab-Controller
├── ui/
│   ├── main_window.py          # Hauptfenster, Tab-Leiste, Statusleiste
│   ├── suppliers.py            # Rechnungssteller-Tab (Liste + Formular)
│   ├── customers.py            # Kunden-Tab (Liste + Suche + Formular)
│   ├── articles.py             # Artikel-Tab (Liste + Formular)
│   ├── invoices.py             # Rechnung-erstellen-Tab
│   ├── archive.py              # Rechnungsarchiv mit Status-Tracking
│   ├── settings.py             # Einstellungen (Pfade, Backup, Nummernkreis)
│   ├── widgets.py              # Wiederverwendbare UI-Komponenten (Cards, Fields, Badges)
│   └── theme.py                # Design-Tokens, QSS-Stylesheet-Generator
├── db/
│   ├── database.py             # SQLite-Verbindung, Schema-Migrationen
│   └── repos/
│       ├── supplier_repo.py    # CRUD Rechnungssteller
│       ├── customer_repo.py    # CRUD Kunden
│       ├── article_repo.py     # CRUD Artikel
│       ├── invoice_repo.py     # CRUD Rechnungen + Positionen
│       └── number_repo.py      # Rechnungsnummern-Verwaltung
├── models/
│   ├── supplier.py             # Dataclass Supplier
│   ├── customer.py             # Dataclass Customer
│   ├── article.py              # Dataclass Article
│   ├── invoice.py              # Dataclass Invoice + InvoiceLine
│   └── enums.py                # InvoiceStatus, RabattTyp, MwstSatz
├── export/
│   ├── pdf_generator.py        # ReportLab-basierte PDF-Erzeugung
│   ├── zugferd_generator.py    # Factur-X XML + PDF/A-3 Embedding
│   └── backup.py               # JSON-Export/Import aller Daten
├── utils/
│   ├── invoice_numbers.py      # RE-JJJJ-NNNN Logik
│   ├── validation.py           # Eingabevalidierung
│   ├── paths.py                # AppData/Dokumente Pfad-Helpers
│   └── calculations.py         # Netto/MwSt/Brutto/Rabatt-Berechnungen
├── assets/
│   └── style.qss               # Qt-Stylesheet
├── requirements.txt
└── README.md
```

---

## 5. Datenmodell (SQLite)

### 5.1 Tabelle: `suppliers`

| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Primärschlüssel |
| `firma` | TEXT NOT NULL | Firmenname |
| `inhaber` | TEXT | Inhaber / Geschäftsführer |
| `strasse` | TEXT | Straße & Hausnummer |
| `plz` | TEXT | Postleitzahl |
| `ort` | TEXT | Ort |
| `postfach` | TEXT | Postfach |
| `telefon` | TEXT | Telefon 1 |
| `telefon2` | TEXT | Telefon 2 |
| `mobil` | TEXT | Mobilnummer |
| `telefax` | TEXT | Telefax |
| `email` | TEXT | E-Mail-Adresse |
| `web` | TEXT | Webseite |
| `steuernr` | TEXT | Steuernummer |
| `ustid` | TEXT | Umsatzsteuer-ID |
| `bank` | TEXT | Kreditinstitut |
| `iban` | TEXT | IBAN |
| `bic` | TEXT | BIC/SWIFT |
| `logo_path` | TEXT | Pfad zum Logo (relativ zu logos/) |
| `dankessatz` | TEXT | Standard-Dankestext |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Erstellungsdatum |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Letzte Änderung |

### 5.2 Tabelle: `customers`

| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Primärschlüssel |
| `anrede` | TEXT | Herr / Frau / Firma / Diverse |
| `titel` | TEXT | Dr. / Prof. etc. |
| `vorname` | TEXT NOT NULL | Vorname |
| `nachname` | TEXT NOT NULL | Nachname |
| `firma` | TEXT | Firmenname (optional) |
| `strasse` | TEXT | Straße & Hausnr. |
| `plz` | TEXT | PLZ |
| `ort` | TEXT | Ort |
| `email` | TEXT | E-Mail |
| `telefon` | TEXT | Telefon |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Erstellungsdatum |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Letzte Änderung |

### 5.3 Tabelle: `articles`

| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Primärschlüssel |
| `bezeichnung` | TEXT NOT NULL | Artikelbezeichnung |
| `beschreibung` | TEXT | Optionale Beschreibung |
| `preis` | REAL NOT NULL | Nettopreis in EUR |
| `mwst` | REAL NOT NULL DEFAULT 19 | MwSt-Satz (0, 7, 19) |
| `beguenstigt_35a` | BOOLEAN DEFAULT 0 | Begünstigt nach §35a EStG |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Erstellungsdatum |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Letzte Änderung |

### 5.4 Tabelle: `invoices`

| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Primärschlüssel |
| `supplier_id` | INTEGER FK → suppliers | Rechnungssteller |
| `customer_id` | INTEGER FK → customers | Empfänger |
| `rechnungsnr` | TEXT UNIQUE NOT NULL | z.B. RE-2026-0001 |
| `datum` | DATE NOT NULL | Rechnungsdatum |
| `betreff` | TEXT | Betreffzeile |
| `objekt_weg` | TEXT | Objekt / WEG |
| `ausfuehrungsdatum` | DATE | Tag der Ausführung |
| `zeitraum_von` | DATE | Ausführungszeitraum von |
| `zeitraum_bis` | DATE | Ausführungszeitraum bis |
| `zahlungsziel` | INTEGER DEFAULT 14 | Zahlungsziel in Tagen |
| `rabatt_typ` | TEXT | 'prozent' oder 'betrag' |
| `rabatt_wert` | REAL DEFAULT 0 | Rabattwert |
| `lohnanteil_35a` | REAL DEFAULT 0 | Lohnanteil §35a in EUR |
| `geraeteanteil_35a` | REAL DEFAULT 0 | Geräteanteil §35a in EUR |
| `dankessatz` | TEXT | Dankestext |
| `hinweise` | TEXT | Weitere Hinweise |
| `status` | TEXT DEFAULT 'entwurf' | 'entwurf' / 'versendet' / 'bezahlt' |
| `netto` | REAL | Berechneter Nettobetrag |
| `mwst_betrag` | REAL | Berechnete MwSt gesamt |
| `brutto` | REAL | Berechneter Bruttobetrag |
| `pdf_path` | TEXT | Pfad zur exportierten PDF |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Erstellungsdatum |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Letzte Änderung |

### 5.5 Tabelle: `invoice_lines`

| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Primärschlüssel |
| `invoice_id` | INTEGER FK → invoices ON DELETE CASCADE | Zugehörige Rechnung |
| `position` | INTEGER | Positionsnummer (1, 2, 3…) |
| `article_id` | INTEGER FK → articles | Verknüpfter Artikel (optional) |
| `beschreibung` | TEXT NOT NULL | Positionstext |
| `menge` | REAL NOT NULL | Menge |
| `einzelpreis` | REAL NOT NULL | Einzelpreis netto |
| `mwst` | REAL NOT NULL | MwSt-Satz |
| `beguenstigt_35a` | BOOLEAN DEFAULT 0 | Begünstigt nach §35a |
| `gesamt_netto` | REAL | Menge × Einzelpreis |

### 5.6 Tabelle: `invoice_numbers`

| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Primärschlüssel |
| `jahr` | INTEGER UNIQUE NOT NULL | Geschäftsjahr (z.B. 2026) |
| `letzter_zaehler` | INTEGER DEFAULT 0 | Letzter vergebener Zähler |

**Logik:** Beim Erzeugen einer neuen Rechnung → Zähler für aktuelles Jahr inkrementieren → Format: `RE-{JJJJ}-{NNNN:04d}`

### 5.7 SQL-Schema (Initialisierung)

```sql
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
    anrede TEXT DEFAULT 'Herr',
    titel TEXT,
    vorname TEXT NOT NULL,
    nachname TEXT NOT NULL,
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
    zeitraum_von DATE,
    zeitraum_bis DATE,
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
```

---

## 6. Feature-Spezifikation

### 6.1 Rechnungssteller-Verwaltung

- CRUD-Operationen: Anlegen, Bearbeiten, Löschen
- Felder: Firma, Inhaber, Adresse (Straße/PLZ/Ort/Postfach), Telefon 1+2, Mobil, Telefax, E-Mail, Web
- Steuerdaten: Steuernummer, USt-IdNr.
- Bankverbindung: Kreditinstitut, IBAN, BIC
- **Logo-Upload:** PNG/JPG, max. 2 MB, Vorschau im Formular, wird auf Rechnung gedruckt
- Standard-Dankessatz: wird bei neuen Rechnungen vorausgefüllt
- Tabellarische Übersicht mit Doppelklick zum Bearbeiten

### 6.2 Kundenverwaltung

- CRUD-Operationen mit Suchfunktion (über Name, Firma, Ort)
- Felder: Anrede (Herr/Frau/Firma/Diverse), Titel, Vorname, Nachname, Firma, Adresse, E-Mail, Telefon
- Tabellarische Übersicht, filterbar

### 6.3 Artikelverwaltung

- CRUD-Operationen
- Felder: Bezeichnung, Beschreibung, Nettopreis, MwSt-Satz (0% / 7% / 19%)
- Checkbox: Begünstigt nach §35a EStG
- Bruttopreis-Vorschau im Formular
- Tabellarische Übersicht mit §35a-Badge

### 6.4 Rechnungserstellung

#### Kopfdaten

- Auswahl Rechnungssteller (Dropdown mit Vorschau der Stammdaten)
- Auswahl Kunde (Dropdown mit Vorschau der Adresse)
- Rechnungsnummer: automatisch (RE-JJJJ-NNNN) oder manuell überschreibbar
- Rechnungsdatum (Datepicker, Default: heute)
- Zahlungsziel in Tagen (Default: 14)
- Tag der Ausführung (Datepicker)
- Ausführungszeitraum von–bis
- Betreffzeile (Freitext)
- Objekt / WEG (Freitext, optional)

#### Positionen

- Dynamische Tabelle: Positionen hinzufügen/entfernen
- Pro Position: Artikel-Auswahl (auto-fill Preis/MwSt/Beschreibung/§35a), Beschreibung, Menge, Einzelpreis, MwSt-Satz, §35a-Checkbox
- Echtzeit-Berechnung: Zeilensumme, Netto, MwSt nach Satz gruppiert, Brutto

#### Rabatt

- Optional aktivierbar
- Typ: Prozent (%) oder fester Betrag (€)
- Wird anteilig auf MwSt-Sätze verteilt
- Anzeige: Netto → Rabatt → Netto nach Rabatt → MwSt → Brutto

#### Zusatzdaten

- Lohnanteil und Geräteanteil nach §35a EStG (EUR-Beträge)
- Dankessatz (vorbefüllt aus Rechnungssteller-Stammdaten)
- Weitere Hinweise (Freitext, z.B. Skonto)

#### Berechnungslogik

```python
# Pro Position
gesamt_netto = menge * einzelpreis

# Gesamtrechnung
netto = sum(position.gesamt_netto for position in positionen)

# Rabatt
if rabatt_typ == 'prozent':
    rabatt_betrag = netto * (rabatt_wert / 100)
else:
    rabatt_betrag = rabatt_wert

netto_nach_rabatt = netto - rabatt_betrag

# MwSt anteilig nach Rabatt
for satz in mwst_saetze:
    anteil = summe_positionen_mit_satz / netto
    mwst_betrag[satz] = (summe_positionen_mit_satz - rabatt_betrag * anteil) * (satz / 100)

mwst_gesamt = sum(mwst_betrag.values())
brutto = netto_nach_rabatt + mwst_gesamt

# §35a Summe
sum_35a = sum(pos.gesamt_netto for pos in positionen if pos.beguenstigt_35a)
```

### 6.5 Rechnungsarchiv & Status-Tracking

- Liste aller erstellten Rechnungen: sortierbar nach Datum, Nummer, Kunde, Betrag
- Suchfunktion über Rechnungsnummer, Kundenname, Betreff
- Status-Workflow: **Entwurf → Versendet → Bezahlt**
  - **Entwurf:** Rechnung editierbar, noch nicht exportiert
  - **Versendet:** PDF wurde exportiert, Änderungen mit Warnung möglich
  - **Bezahlt:** Rechnung abgeschlossen, nur noch Ansicht + erneuter Export
- Doppelklick auf Eintrag öffnet Rechnung zur Ansicht/Bearbeitung
- Schnell-Aktionen: PDF öffnen, Status ändern, Rechnung duplizieren

### 6.6 PDF-Export

- Professionelles A4-Layout via ReportLab
- Firmenlogo oben links (aus Rechnungssteller-Stammdaten)
- Absender-Kurzzeile + Empfänger-Adressblock
- Rechnungsnummer, Datum, Zahlungsziel, Ausführungsdatum/-zeitraum
- Betreff fett hervorgehoben
- Objekt/WEG falls angegeben
- Positionstabelle: Pos. | Beschreibung | Menge | Einzelpreis | MwSt | Gesamt
- Netto/Rabatt/MwSt/Brutto-Zusammenfassung
- §35a-Hinweis mit Lohn- und Geräteanteil (falls > 0)
- Dankessatz + Hinweise
- Fußzeile (dreispaltig): Bankverbindung | Steuerdaten | Kontaktdaten
- **Speicherort:** `Dokumente\Rechnungen\Rechnungen - MMJJJJ\RE-JJJJ-NNNN.pdf`

### 6.7 ZUGFeRD-Export (EN16931 / COMFORT)

- **Profil:** COMFORT (EN16931-konform, zukunftssicher für E-Rechnung)
- XML-Datei: `factur-x.xml` gemäß Cross Industry Invoice (CII) Schema
- Einbettung: XML als Attachment in PDF/A-3b (via Factur-X Python-Library)
- Validierung: gegen offizielle Schematron-Regeln vor Export
- Fallback: Bei Validierungsfehler → Warnung anzeigen, reines PDF ohne ZUGFeRD anbieten
- Ausgabe: gleicher Speicherort wie PDF

#### Pflichtfelder im ZUGFeRD-XML

| BT/BG-Code | Feld | Quelle |
|---|---|---|
| BT-1 | Rechnungsnummer | `invoices.rechnungsnr` |
| BT-2 | Rechnungsdatum | `invoices.datum` |
| BT-3 | Rechnungstyp-Code | 380 (Commercial Invoice) |
| BT-5 | Währung | EUR |
| BT-9 | Zahlungsfälligkeitsdatum | `datum + zahlungsziel` |
| BG-4 | Verkäufer | `suppliers.*` (Name, Adresse, Steuernr/USt-ID) |
| BG-7 | Käufer | `customers.*` (Name, Adresse) |
| BG-16 | Zahlungsanweisungen | `suppliers.iban`, `suppliers.bic` |
| BG-22 | Gesamtbeträge | Netto, MwSt, Brutto |
| BG-25 | Rechnungspositionen | `invoice_lines.*` (Menge, Preis, MwSt-Satz, Betrag) |

#### Technischer Workflow

```
1. PDF erzeugen (ReportLab)
2. XML generieren (Factur-X / lxml)
3. Schematron-Validierung
4. XML in PDF einbetten → PDF/A-3b
5. Speichern
```

### 6.8 Automatische Rechnungsnummern

- Format: `RE-JJJJ-NNNN` (z.B. RE-2026-0001)
- Fortlaufend pro Kalenderjahr, bei Jahreswechsel automatischer Reset auf 0001
- Gespeichert in Tabelle `invoice_numbers`
- Manuelles Überschreiben möglich (Warnung bei Lücken/Duplikaten)

### 6.9 Logo-Upload

- Dateiformate: PNG, JPG (max. 2 MB)
- Gespeichert unter `%APPDATA%\Rechnungsprogramm\logos\{supplier_id}.png`
- Vorschau im Rechnungssteller-Formular
- Wird auf PDF oben links gerendert (max. Höhe: 25mm)

### 6.10 Datensicherung / Backup

- **Manueller Export:** Alle Daten als JSON-Datei (Speichern-unter-Dialog)
- **Manueller Import:** JSON einlesen mit Konflikterkennung (bestehende Daten überschreiben oder zusammenführen)
- **Automatisches Backup:** Täglich beim App-Start (in `%APPDATA%\backups\`, letzte 10 behalten)
- **JSON-Struktur:**
  ```json
  {
    "meta": { "version": "1.0", "exported_at": "2026-02-16T10:30:00" },
    "suppliers": [...],
    "customers": [...],
    "articles": [...],
    "invoices": [...],
    "invoice_lines": [...],
    "invoice_numbers": [...]
  }
  ```

---

## 7. UI/UX-Spezifikation

Das UI-Design basiert auf dem erstellten React-Prototyp, wird jedoch für die Desktop-Nutzung optimiert.

### 7.1 Design-Prinzipien

- **Clean & Modern:** Helle Oberfläche, klare Typografie, großzügiger Whitespace
- **Effizienz:** Tastaturnavigation, Tab-Reihenfolge, Shortcuts
- **Konsistenz:** Einheitliche Formulargestaltung, gleiche Patterns über alle Tabs
- **Feedback:** Erfolgsmeldungen, Validierungsfehler inline, Ladeanzeigen

### 7.2 Hauptfenster-Layout

- Fenstergröße: 1200×800 px (minimum), skalierbar
- Header: Logo-Icon + Titel, dezent
- Tab-Leiste: Horizontal, Icons + Labels (Rechnungssteller, Kunden, Artikel, Rechnung erstellen, Archiv)
- Content-Bereich: Scrollbar, max-width begrenzt für Lesbarkeit
- Statusleiste: Datenbankpfad, letzte Aktion, Version

### 7.3 Design-Tokens (QSS)

| Token | Wert | Verwendung |
|---|---|---|
| `--bg` | `#F7F8FA` | Haupthintergrund |
| `--surface` | `#FFFFFF` | Karten, Formulare |
| `--border` | `#E5E7EB` | Ränder, Trennlinien |
| `--primary` | `#4F46E5` (Indigo) | Buttons, aktive Tabs, Akzente |
| `--text` | `#111827` | Primärtext |
| `--text-secondary` | `#6B7280` | Labels, Platzhalter |
| `--danger` | `#DC2626` | Lösch-Aktionen, Fehler |
| `--success` | `#059669` | §35a-Badges, Bezahlt-Status |
| `--warn` | `#D97706` | Rabatt-Sektion, Entwurf-Status |
| `--font` | `Segoe UI, 10pt` | Standard-Systemfont |
| `--font-mono` | `Consolas, 10pt` | Beträge, Rechnungsnummern |
| `--radius` | `8px` | Karten, Buttons |

### 7.4 Keyboard-Shortcuts

| Shortcut | Aktion |
|---|---|
| `Strg + N` | Neuen Eintrag anlegen (kontextabhängig) |
| `Strg + S` | Aktuelles Formular speichern |
| `Strg + P` | PDF-Export der aktuellen Rechnung |
| `Strg + F` | Suchfeld fokussieren |
| `Strg + 1–5` | Tab wechseln |
| `Entf` | Markierten Eintrag löschen (mit Bestätigung) |
| `Escape` | Formular schließen / Zurück zur Liste |

---

## 8. PDF-Layout-Spezifikation (Detailliert)

### 8.1 Seitenformat & Grundeinstellungen

| Eigenschaft | Wert |
|---|---|
| Format | A4 Hochformat (210 × 297 mm) |
| Rand links | 20 mm |
| Rand rechts | 20 mm |
| Rand oben | 15 mm |
| Rand unten | 20 mm (Fußzeile eingerechnet) |
| Nutzbare Breite | 170 mm |
| Schriftart Body | Helvetica, 10pt |
| Schriftart Überschriften | Helvetica-Bold |
| Schriftart Beträge | Helvetica, rechtsbündig |
| Farbe Text | #111827 |
| Farbe Grau (Labels) | #6B7280 |
| Farbe Linien | #D1D5DB |
| Farbe Akzent (Summenzeile) | #1E40AF |

### 8.2 Layout-Zonen (Y-Positionen von oben, in mm)

```
┌─────────────────────────────────────────────────────────────┐
│  15mm  ZONE 1: Kopfbereich (Logo + Firmendaten)            │
│        Y: 15–45mm                                           │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │  LOGO        │    │  Firmenname (Bold, 14pt)         │   │
│  │  max 50×25mm │    │  Inhaber                         │   │
│  │  links       │    │  Straße                 rechts   │   │
│  └──────────────┘    │  PLZ Ort                         │   │
│                      │  Tel: | Fax: | Mobil:            │   │
│                      │  E-Mail: | Web:                  │   │
│                      └──────────────────────────────────┘   │
│─────────────────────────────────────────────────────────────│
│  45mm  Trennlinie (0.5pt, #D1D5DB)                         │
│─────────────────────────────────────────────────────────────│
│  47mm  ZONE 2: Absenderzeile (klein, 7pt, grau)            │
│        "Firma · Straße · PLZ Ort"                          │
│─────────────────────────────────────────────────────────────│
│  50mm  ZONE 3: Adressfeld + Rechnungsinfo (nebeneinander)  │
│        Y: 50–85mm                                           │
│  ┌─────────────────────┐  ┌────────────────────────────┐   │
│  │  EMPFÄNGER (links)  │  │  RECHNUNGSINFO (rechts)    │   │
│  │  85mm breit         │  │  75mm breit                │   │
│  │                     │  │                            │   │
│  │  {Anrede Titel}     │  │  Rechnungsnr:  RE-JJJJ-N  │   │
│  │  {Vorname Nachname} │  │  Datum:        DD.MM.JJJJ │   │
│  │  {Firma}            │  │  Kunden-Nr:    K-{id}      │   │
│  │  {Straße}           │  │  Zahlungsziel: DD.MM.JJJJ │   │
│  │  {PLZ Ort}          │  │                            │   │
│  └─────────────────────┘  └────────────────────────────┘   │
│─────────────────────────────────────────────────────────────│
│  88mm  ZONE 4: Betreff                                      │
│        Schrift: Helvetica-Bold, 12pt                        │
│        Quelle: invoices.betreff                             │
│─────────────────────────────────────────────────────────────│
│  95mm  ZONE 5: Objekt/WEG (nur wenn gefüllt)               │
│        "Objekt: {invoices.objekt_weg}"                      │
│        Schrift: 10pt, normal                                │
│─────────────────────────────────────────────────────────────│
│  100mm ZONE 6: Ausführungshinweis (nur wenn gefüllt)        │
│        Variante A (einzelner Tag):                          │
│          "Leistungsdatum: DD.MM.JJJJ"                      │
│        Variante B (Zeitraum):                               │
│          "Leistungszeitraum: DD.MM.JJJJ – DD.MM.JJJJ"     │
│        Schrift: 10pt, normal                                │
│─────────────────────────────────────────────────────────────│
│  105mm ZONE 7: Positionstabelle                             │
│        (Details siehe 8.3)                                  │
│─────────────────────────────────────────────────────────────│
│        ZONE 8: Summenblock                                  │
│        (Details siehe 8.4)                                  │
│─────────────────────────────────────────────────────────────│
│        ZONE 9: §35a-Hinweis (nur wenn Anteile > 0)         │
│        (Details siehe 8.5)                                  │
│─────────────────────────────────────────────────────────────│
│        ZONE 10: Dankessatz + Hinweise                       │
│        (Details siehe 8.6)                                  │
│─────────────────────────────────────────────────────────────│
│  unten ZONE 11: Fußzeile (dreispaltig)                      │
│        (Details siehe 8.7)                                  │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Positionstabelle (ZONE 7)

#### Tabellenheader

| Spalte | Breite (mm) | Ausrichtung | Überschrift |
|---|---|---|---|
| Pos. | 10 | rechts | `Pos.` |
| Beschreibung | 75 | links | `Beschreibung` |
| Menge | 20 | rechts | `Menge` |
| Einzelpreis | 25 | rechts | `Einzelpreis` |
| MwSt | 15 | rechts | `MwSt` |
| Gesamt | 25 | rechts | `Gesamt` |
| **Summe** | **170** | | |

- Header: Helvetica-Bold, 9pt, Hintergrund `#F3F4F6`, obere+untere Linie 0.75pt `#D1D5DB`
- Zeilen: Helvetica, 9pt, untere Linie 0.5pt `#E5E7EB`
- Letzte Zeile: untere Linie 1pt `#111827`

#### Feldzuordnung pro Zeile

| PDF-Spalte | Datenquelle | Format |
|---|---|---|
| Pos. | `invoice_lines.position` | `{n}` (1, 2, 3…) |
| Beschreibung | `invoice_lines.beschreibung` | Text, Zeilenumbruch bei > 75mm |
| Menge | `invoice_lines.menge` | `{:.2f}` (z.B. "1,00") |
| Einzelpreis | `invoice_lines.einzelpreis` | `{:.2f} €` (z.B. "45,00 €") |
| MwSt | `invoice_lines.mwst` | `{:.0f}%` (z.B. "19%") |
| Gesamt | `invoice_lines.gesamt_netto` | `{:.2f} €` (z.B. "45,00 €") |

### 8.4 Summenblock (ZONE 8)

Rechts ausgerichtet, Breite 75mm (= Spalten Menge bis Gesamt), 12mm Abstand nach Tabelle.

| Zeile | Label (links) | Wert (rechts) | Bedingung | Stil |
|---|---|---|---|---|
| 1 | `Nettobetrag` | `{invoices.netto:.2f} €` | immer | 10pt normal |
| 2 | `Rabatt ({rabatt_wert}%)` oder `Rabatt` | `−{rabatt_betrag:.2f} €` | nur wenn `rabatt_wert > 0` | 10pt, Farbe #D97706 |
| 3 | `Netto nach Rabatt` | `{netto_nach_rabatt:.2f} €` | nur wenn Rabatt | 10pt bold |
| 4a | `zzgl. 7% MwSt` | `{mwst_7:.2f} €` | nur wenn Positionen mit 7% | 10pt normal |
| 4b | `zzgl. 19% MwSt` | `{mwst_19:.2f} €` | nur wenn Positionen mit 19% | 10pt normal |
| 5 | **`Bruttobetrag`** | **`{invoices.brutto:.2f} €`** | immer | **12pt bold**, obere Linie 1.5pt #1E40AF |

- Trennlinie über Bruttobetrag: 1.5pt, Farbe `#1E40AF`
- Alle Beträge: Helvetica, rechtsbündig, deutsches Format (Komma als Dezimal, Punkt als Tausender)

### 8.5 §35a-Hinweisbox (ZONE 9, nur wenn Anteile > 0)

Wird angezeigt wenn `lohnanteil_35a > 0` ODER `geraeteanteil_35a > 0`. 8mm Abstand nach Summenblock.

```
┌─────────────────────────────────────────────────────────────┐
│  Hintergrund: #F0FDF4 (hellgrün)                            │
│  Rahmen: 0.5pt #BBF7D0                                      │
│  Padding: 8mm                                                │
│                                                              │
│  "Begünstigte Anteile nach §35a EStG"  (Bold, 9pt)         │
│                                                              │
│  "In dem Rechnungsbetrag von {brutto} € sind folgende"      │
│  "begünstigte Anteile enthalten:"        (9pt, normal)      │
│                                                              │
│  "Lohnkosten:          {lohnanteil_35a:.2f} €"  (wenn > 0) │
│  "Geräte-/Maschinen:   {geraeteanteil_35a:.2f} €" (w > 0) │
│  "Gesamt §35a:          {lohn + geraet:.2f} €"   (Bold)    │
└─────────────────────────────────────────────────────────────┘
```

#### Feldzuordnung

| PDF-Text | Datenquelle |
|---|---|
| Rechnungsbetrag | `invoices.brutto` |
| Lohnkosten | `invoices.lohnanteil_35a` |
| Geräte-/Maschinenkosten | `invoices.geraeteanteil_35a` |
| Gesamt §35a | `lohnanteil_35a + geraeteanteil_35a` |

### 8.6 Dankessatz & Hinweise (ZONE 10)

8mm Abstand nach §35a-Box (oder nach Summenblock wenn keine §35a-Box).

| Element | Datenquelle | Stil |
|---|---|---|
| Dankessatz | `invoices.dankessatz` | Helvetica, 10pt, normal, Farbe #374151 |
| (Leerzeile) | — | 4mm Abstand |
| Hinweise | `invoices.hinweise` | Helvetica, 9pt, kursiv, Farbe #6B7280, nur wenn gefüllt |

### 8.7 Fußzeile (ZONE 11, am Seitenende)

Feste Position: 20mm vom unteren Seitenrand. Dreispaltig, obere Trennlinie 0.75pt `#D1D5DB`.

| Spalte | Breite | Inhalt | Datenquelle |
|---|---|---|---|
| Links (Bankverbindung) | 57mm | `Bankverbindung` (Bold, 7pt) | — |
| | | `{suppliers.bank}` | `suppliers.bank` |
| | | `IBAN: {suppliers.iban}` | `suppliers.iban` |
| | | `BIC: {suppliers.bic}` | `suppliers.bic` |
| Mitte (Steuerdaten) | 57mm | `Steuerdaten` (Bold, 7pt) | — |
| | | `St.-Nr.: {suppliers.steuernr}` | `suppliers.steuernr` |
| | | `USt-IdNr.: {suppliers.ustid}` | `suppliers.ustid` |
| Rechts (Kontakt) | 56mm | `Kontakt` (Bold, 7pt) | — |
| | | `Tel: {suppliers.telefon}` | `suppliers.telefon` |
| | | `Fax: {suppliers.telefax}` | `suppliers.telefax` (nur wenn gefüllt) |
| | | `{suppliers.email}` | `suppliers.email` |
| | | `{suppliers.web}` | `suppliers.web` (nur wenn gefüllt) |

- Alle Fußzeilen-Texte: Helvetica, 7pt, Farbe `#6B7280`
- Labels (Bankverbindung, Steuerdaten, Kontakt): Helvetica-Bold, 7pt

### 8.8 Kopfbereich — Feldzuordnung (ZONE 1)

| PDF-Element | Datenquelle | Position | Stil |
|---|---|---|---|
| Logo | Datei aus `suppliers.logo_path` | Links, 20mm vom Rand, max 50×25mm | Bild, proportional skaliert |
| Firmenname | `suppliers.firma` | Rechts oben, rechtsbündig | Helvetica-Bold, 14pt |
| Inhaber | `suppliers.inhaber` | darunter | Helvetica, 9pt |
| Straße | `suppliers.strasse` | darunter | Helvetica, 9pt, Farbe #6B7280 |
| PLZ Ort | `suppliers.plz` + ` ` + `suppliers.ort` | darunter | Helvetica, 9pt, Farbe #6B7280 |
| Telefon | `Tel: ` + `suppliers.telefon` | darunter | Helvetica, 8pt, Farbe #6B7280 |
| E-Mail | `suppliers.email` | darunter | Helvetica, 8pt, Farbe #6B7280 |

### 8.9 Empfängerblock — Feldzuordnung (ZONE 3 links)

Position gemäß DIN 5008: links 20mm, Y ca. 50mm. Fenster für Briefumschlag C6/5.

| Zeile | Datenquelle | Bedingung |
|---|---|---|
| 1 | `customers.firma` | nur wenn gefüllt |
| 2 | `customers.anrede` + ` ` + `customers.titel` + ` ` + `customers.vorname` + ` ` + `customers.nachname` | immer (Titel nur wenn gefüllt) |
| 3 | `customers.strasse` | immer |
| 4 | `customers.plz` + ` ` + `customers.ort` | immer |

Stil: Helvetica, 10pt, Farbe #111827.

### 8.10 Rechnungsinfo-Block — Feldzuordnung (ZONE 3 rechts)

Tabellarisch, Label links (grau 8pt), Wert rechts (10pt bold).

| Label | Wert | Datenquelle | Format |
|---|---|---|---|
| `Rechnungsnr.` | RE-2026-0001 | `invoices.rechnungsnr` | direkt |
| `Rechnungsdatum` | 16.02.2026 | `invoices.datum` | `DD.MM.JJJJ` |
| `Kunden-Nr.` | K-42 | `"K-" + str(customers.id)` | `K-{id}` |
| `Zahlbar bis` | 02.03.2026 | `invoices.datum + zahlungsziel Tage` | `DD.MM.JJJJ` |

### 8.11 Mehrseitige Rechnungen

- Positionstabelle wird automatisch umgebrochen wenn sie über den verfügbaren Platz hinausgeht
- Auf Folgeseiten: Tabellen-Header wird wiederholt
- Summenblock, §35a-Box, Dankessatz, Hinweise erscheinen immer auf der letzten Seite
- Fußzeile wird auf jeder Seite gedruckt
- Seitenzahl: nur wenn > 1 Seite, Format "Seite {n} von {gesamt}" zentriert über Fußzeile

### 8.12 Beispiel-Rechnung (Textrepräsentation)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  [LOGO]                              Mustermann Gartenbau GmbH          │
│                                      Max Mustermann                      │
│                                      Gartenweg 12                        │
│                                      71332 Waiblingen                    │
│                                      Tel: 07151 123456                   │
│                                      info@mustermann-garten.de           │
│                                                                          │
│  ─────────────────────────────────────────────────────────────────────── │
│  Mustermann Gartenbau GmbH · Gartenweg 12 · 71332 Waiblingen           │
│                                                                          │
│  Herrn                                 Rechnungsnr.    RE-2026-0003     │
│  Dr. Hans Schmidt                      Rechnungsdatum  16.02.2026       │
│  Ahornstraße 45                        Kunden-Nr.      K-12             │
│  71334 Waiblingen                      Zahlbar bis     02.03.2026       │
│                                                                          │
│                                                                          │
│  Rechnung für Gartenpflege Januar 2026                                  │
│                                                                          │
│  Objekt: WEG Birkenallee 10-14, 71332 Waiblingen                       │
│                                                                          │
│  Leistungszeitraum: 06.01.2026 – 31.01.2026                            │
│                                                                          │
│  ┌──────┬──────────────────────────┬────────┬───────────┬──────┬────────┐│
│  │ Pos. │ Beschreibung             │  Menge │ Einzelpr. │ MwSt │ Gesamt ││
│  ├──────┼──────────────────────────┼────────┼───────────┼──────┼────────┤│
│  │    1 │ Rasenmähen Gesamtfläche  │   4,00 │  85,00 €  │  19% │340,00 €││
│  │    2 │ Heckenschnitt            │   2,00 │  65,00 €  │  19% │130,00 €││
│  │    3 │ Laubbeseitigung          │   1,00 │ 120,00 €  │  19% │120,00 €││
│  │    4 │ Streumittel Winter       │   3,00 │  12,50 €  │  19% │ 37,50 €││
│  └──────┴──────────────────────────┴────────┴───────────┴──────┴────────┘│
│                                                                          │
│                                           Nettobetrag      627,50 €     │
│                                           zzgl. 19% MwSt   119,23 €     │
│                                           ════════════════════════════   │
│                                           Bruttobetrag     746,73 €     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Begünstigte Anteile nach §35a EStG                                │  │
│  │ In dem Rechnungsbetrag von 746,73 € sind enthalten:               │  │
│  │ Lohnkosten:              480,00 €                                 │  │
│  │ Geräte-/Maschinenkosten:  85,00 €                                 │  │
│  │ Gesamt §35a:             565,00 €                                 │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Vielen Dank für Ihren Auftrag!                                         │
│                                                                          │
│  ─────────────────────────────────────────────────────────────────────── │
│  Bankverbindung          │ Steuerdaten              │ Kontakt            │
│  Sparkasse Waiblingen    │ St.-Nr.: 12/345/67890    │ Tel: 07151 123456  │
│  IBAN: DE89 3704 0044    │ USt-IdNr.: DE123456789   │ Fax: 07151 123457  │
│  BIC: COBADEFFXXX        │                          │ info@mustermann.de │
│                          │                          │ www.mustermann.de  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Meilensteine & Umsetzungsplan

| Phase | Meilenstein | Umfang | Abhängigkeit |
|---|---|---|---|
| **Phase 1** | Grundgerüst | Projektstruktur, SQLite-Setup, Migrationen, PySide6-Hauptfenster mit Tab-Navigation, QSS-Theming | — |
| **Phase 2** | Stammdaten | Rechnungssteller-CRUD, Kunden-CRUD, Artikel-CRUD inkl. §35a, Logo-Upload | Phase 1 |
| **Phase 3** | Rechnungserstellung | Rechnungsformular komplett, Positionen, Rabatt, §35a, Berechnungen, auto. Rechnungsnummern | Phase 2 |
| **Phase 4** | PDF-Export | ReportLab-Layout, Logo-Integration, alle Rechnungsfelder, Monatsordner-Ablage | Phase 3 |
| **Phase 5** | ZUGFeRD | Factur-X XML, EN16931/COMFORT, PDF/A-3b-Einbettung, Validierung | Phase 4 |
| **Phase 6** | Archiv & Status | Rechnungsliste, Suche, Status-Workflow, Schnellaktionen | Phase 3 |
| **Phase 7** | Backup & Polish | JSON-Export/Import, Auto-Backup, Keyboard-Shortcuts, Fehlerbehandlung, finale Tests | Phase 1–6 |
| **Phase 8** | Distribution | PyInstaller-Build, Inno Setup Installer, README, Dokumentation | Phase 7 |

---

## 10. Risiken & Mitigationen

| Risiko | Auswirkung | Mitigation |
|---|---|---|
| ZUGFeRD-Validierung schlägt fehl | Hoch | Validierung vor Export, Fallback auf reines PDF, Fehlerprotokoll |
| SQLite-Datei beschädigt | Hoch | Tägliches Auto-Backup, WAL-Mode, `PRAGMA integrity_check` |
| Logo-Formate nicht kompatibel | Niedrig | Konvertierung zu PNG bei Upload, Größenbeschränkung |
| Rechnungsnummern-Lücken | Mittel | Warnung bei manueller Vergabe, Audit-Log |
| Performance bei vielen Rechnungen | Niedrig | Indizes auf häufig gesuchte Spalten, Pagination |

---

## 11. Abnahmekriterien

- [ ] Alle Stammdaten (Rechnungssteller, Kunden, Artikel) können angelegt, bearbeitet und gelöscht werden
- [ ] Rechnung kann mit allen Feldern erstellt und als PDF exportiert werden
- [ ] PDF enthält alle Daten korrekt: Logo, Adressen, Positionen, Beträge, §35a-Hinweis, Fußzeile
- [ ] ZUGFeRD-PDF besteht die Validierung gegen EN16931-Schematron
- [ ] Rechnungsnummern werden automatisch fortlaufend vergeben
- [ ] Status-Tracking (Entwurf/Versendet/Bezahlt) funktioniert korrekt
- [ ] JSON-Backup kann exportiert und vollständig wieder importiert werden
- [ ] App startet und läuft stabil unter Windows 10/11
- [ ] Alle Tastatur-Shortcuts funktionieren

---

## 12. Python Dependencies (`requirements.txt`)

```
PySide6>=6.6
reportlab>=4.1
Pillow>=10.0
lxml>=5.0
factur-x>=3.0
```
