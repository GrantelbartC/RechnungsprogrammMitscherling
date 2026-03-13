# Umsetzungsplan KI-Textfunktion

## Ziel

Die Anwendung soll eine KI-gestuetzte Textfunktion erhalten, mit der freie Prompts in brauchbare Geschaeftstexte umgewandelt werden koennen.

Die Funktion soll in zwei Formen verfuegbar sein:

- als eigener Tab `Textassistent`
- als optionaler Button `Mit KI formulieren` im neuen Bereich `Firmenschreiben`

Der Nutzer soll nur einen freien Prompt eingeben muessen. Weitere Angaben sind optional und dienen nur als Komfortfunktion.

## Produktentscheidung

- Provider: NVIDIA API Catalog
- Default-Modell: `minimaxai/minimax-m2.5`
- API-Stil: Chat Completions ueber NVIDIA Endpoint
- Secret-Handling: API-Key in `.env`
- Komforteinstellungen: in `QSettings`

## Nicht-Ziele fuer den MVP

- keine automatische Vollbefuellung ohne Nutzerbestaetigung
- kein Versand von Schreiben per E-Mail
- keine Prompt-Historie
- keine serverseitige Schluesselverwaltung
- kein Multi-User-Berechtigungssystem

## Zielbild

### 1. Textassistent

Ein eigener Tab mit:

- grossem Prompt-Feld
- optionalen Kontext-Schaltern
- Ergebnisfeldern fuer `Betreff`, `Anrede`, `Brieftext`, `Grussformel`
- Buttons fuer Generierung und Uebernahme in `Firmenschreiben`

### 2. Firmenschreiben

Ein eigener Tab mit:

- Auswahl von Rechnungssteller und Kunde
- automatischer FS-Nummer
- Datum
- Betreff
- Anrede
- Brieftext
- Grussformel
- Speichern
- PDF-Export
- KI-Button `Mit KI formulieren`

## Architektur

### Bestehende Basis

Bereits vorhanden:

- Datenmodell `Firmenschreiben`
- DB-Tabelle `firmenschreiben`
- Nummernlogik fuer `FS`
- Exportpfade fuer Firmenschreiben

Bestehende Dateien, auf denen aufgebaut wird:

- `rechnungsprogramm/main.py`
- `rechnungsprogramm/ui/main_window.py`
- `rechnungsprogramm/ui/settings.py`
- `rechnungsprogramm/db/database.py`
- `rechnungsprogramm/models/firmenschreiben.py`
- `rechnungsprogramm/utils/fs_numbers.py`
- `rechnungsprogramm/utils/paths.py`
- `rechnungsprogramm/ui/widgets.py`
- `rechnungsprogramm/ui/mahnwesen.py`
- `rechnungsprogramm/ui/invoices.py`

### Neue Module

#### Services

- `rechnungsprogramm/services/ai_config.py`
- `rechnungsprogramm/services/ai_prompt_builder.py`
- `rechnungsprogramm/services/ai_text_service.py`

#### UI

- `rechnungsprogramm/ui/firmenschreiben.py`
- `rechnungsprogramm/ui/text_assistant.py`
- `rechnungsprogramm/ui/ai_text_dialog.py`
- `rechnungsprogramm/ui/ai_workers.py`

#### Datenzugriff und Export

- `rechnungsprogramm/db/repos/fs_repo.py`
- `rechnungsprogramm/export/fs_pdf_generator.py`

#### Projektdateien

- `.gitignore`
- `.env.example`
- `umsetzungsplan_KI.md`

## Konfigurationskonzept

### `.env`

Die Datei `.env` liegt im Projektroot und wird nicht versioniert.

Beispiel:

```env
TEXT_AI_PROVIDER=nvidia
TEXT_AI_API_KEY=dein_nvidia_key
TEXT_AI_BASE_URL=https://integrate.api.nvidia.com/v1
TEXT_AI_MODEL=minimaxai/minimax-m2.5
```

### `QSettings`

In `QSettings` werden nur nicht-geheime Werte gespeichert:

- bevorzugtes Modell
- Default-Tonalitaet
- `Kundendaten einbeziehen` standardmaessig an oder aus
- `Fuer Firmenschreiben strukturieren` standardmaessig an oder aus

## Datenformat der KI-Antwort

Die KI soll intern immer auf diese Struktur normalisiert werden:

```json
{
  "betreff": "string",
  "anrede": "string",
  "brieftext": "string",
  "grussformel": "string"
}
```

Der Nutzer sieht diese Struktur nicht als technische JSON-Antwort, sondern als editierbare Felder in der UI.

## Datenfluss

1. Nutzer gibt einen freien Prompt ein.
2. Optional wird Kontext aus Kunde und Rechnungssteller ergaenzt.
3. `ai_prompt_builder.py` baut daraus den Request.
4. `ai_text_service.py` sendet den Request an NVIDIA.
5. Die Antwort wird geparst und validiert.
6. Die UI zeigt `Betreff`, `Anrede`, `Brieftext`, `Grussformel` editierbar an.
7. Der Nutzer uebernimmt die Inhalte explizit in `Firmenschreiben`.
8. Das Schreiben kann gespeichert und als PDF exportiert werden.

## Technische Bausteine

### `ai_config.py`

Verantwortung:

- Laden von `.env`
- Bereitstellen einer `AIConfig`-Struktur
- Lesen und Schreiben von UI-Praeferenzen ueber `QSettings`

Geplante Inhalte:

- `AIConfig` dataclass
- `load_ai_config()`
- `load_ai_preferences()`
- `save_ai_preferences()`

### `ai_prompt_builder.py`

Verantwortung:

- aus freiem Prompt und optionalem Kontext einen stabilen Prompt bauen
- die Ausgabe auf die vier Zielfelder ausrichten

Geplante Inhalte:

- `LetterContext` dataclass
- `build_generation_messages(prompt, context, tone, structured=True)`
- `build_revision_messages(current_draft, instruction, context)`

### `ai_text_service.py`

Verantwortung:

- HTTP-Aufruf an NVIDIA
- Fehlerbehandlung
- Parsing und Validierung
- Rueckgabe einer sauberen Datenstruktur fuer die UI

Geplante Inhalte:

- `AITextService.generate_letter(...)`
- `AITextService.revise_letter(...)`
- `_post_chat_completion(messages, model)`
- `_extract_structured_result(raw_text)`

### `ai_workers.py`

Verantwortung:

- asynchrone Ausfuehrung, damit die UI nicht blockiert

Geplante Inhalte:

- `GenerateLetterWorker(QObject)`
- Signal `finished(dict)`
- Signal `failed(str)`

### `fs_repo.py`

Verantwortung:

- CRUD fuer `firmenschreiben`

Geplante Inhalte:

- `get_all()`
- `get_by_id()`
- `search()`
- `create()`
- `update()`
- `update_status()`
- `update_pdf_path()`
- `delete()`

### `fs_pdf_generator.py`

Verantwortung:

- PDF-Erstellung fuer Firmenschreiben

Inhalt:

- Brieflayout aehnlich zu vorhandenen Dokumenten
- Nutzung des Exportpfads fuer Firmenschreiben
- Rueckgabe des finalen PDF-Pfads

### `firmenschreiben.py`

Verantwortung:

- kompletter UI-Tab fuer Firmenschreiben

Geplante Methoden:

- `_build_kopfdaten()`
- `_build_textbereich()`
- `_build_buttons()`
- `_refresh_dropdowns()`
- `_generate_number()`
- `_read_firmenschreiben()`
- `load_firmenschreiben(fs)`
- `apply_generated_text(data)`
- `_open_ai_dialog()`
- `_export_pdf()`

### `ai_text_dialog.py`

Verantwortung:

- freier Prompt direkt aus dem Firmenschreiben-Flow

Funktionen:

- Prompt-Feld
- optionale Kontextnutzung
- Generieren
- Vorschau
- `Alles uebernehmen`
- `Nur Brieftext uebernehmen`

### `text_assistant.py`

Verantwortung:

- freier Arbeitsbereich fuer KI-Textgenerierung

Geplante Methoden:

- `_build_prompt_area()`
- `_build_result_area()`
- `_generate()`
- `_revise(instruction)`
- `_send_to_firmenschreiben()`

## UI-Konzept

### Textassistent

Elemente:

- Titel `Textassistent`
- grosses Prompt-Feld
- Checkbox `Kundendaten einbeziehen`
- Checkbox `Fuer Firmenschreiben strukturieren`
- Dropdown `Tonalitaet`
- Buttons:
  - `Generieren`
  - `Neu formulieren`
  - `Kuerzer`
  - `Formeller`
  - `Freundlicher`
- Ergebnisfelder:
  - `Betreff`
  - `Anrede`
  - `Brieftext`
  - `Grussformel`
- Uebernahmebutton:
  - `In Firmenschreiben uebernehmen`

### Firmenschreiben

Elemente:

- Rechnungssteller
- Kunde
- FS-Nr.
- Datum
- Betreff
- Anrede
- Brieftext
- Grussformel
- Buttons:
  - `Neue Schreiben`
  - `Speichern`
  - `PDF exportieren`
  - `Mit KI formulieren`

Hinweis:

Der Button `Mit KI formulieren` oeffnet einen Dialog und nicht einen komplett getrennten Workflow.

## Implementierungsphasen

### Phase 0 - Projektbasis

Ziel:

- Grundgeruest fuer Secrets und KI-Konfiguration schaffen

Aufgaben:

- `.gitignore` anlegen
- `.env.example` anlegen
- `python-dotenv` zu `requirements.txt`
- `requests` zu `requirements.txt`
- `.env` in `main.py` laden
- `services/`-Ordner anlegen
- `ai_config.py` anlegen

Abnahme:

- App startet weiter normal
- fehlender API-Key fuehrt nicht zum Absturz

### Phase 1 - Firmenschreiben Persistence

Ziel:

- Datenzugriff fuer Firmenschreiben vollstaendig

Aufgaben:

- `fs_repo.py` anlegen
- Mapping DB <-> Modell umsetzen
- Suchfunktion bauen
- Update- und Delete-Funktionen ergaenzen

Abnahme:

- Firmenschreiben koennen erstellt, geladen, aktualisiert und geloescht werden

### Phase 2 - PDF Export Firmenschreiben

Ziel:

- Exportstrecke fuer Firmenschreiben

Aufgaben:

- `fs_pdf_generator.py` anlegen
- Layout definieren
- Speicherpfad ueber `get_fs_pdf_path()` verwenden
- PDF nach Export oeffnen

Abnahme:

- Aus einem gespeicherten Datensatz entsteht ein oeffenbares PDF

### Phase 3 - AI Service

Ziel:

- funktionierender Request an NVIDIA

Aufgaben:

- `ai_prompt_builder.py`
- `ai_text_service.py`
- NVIDIA Chat Completions anbinden
- JSON-Extraktion robust machen
- Fehlerbehandlung fuer:
  - fehlenden Key
  - Timeout
  - HTTP-Fehler
  - ungueltige Antwort

Abnahme:

- Ein Test-Request liefert ein Dict mit `betreff`, `anrede`, `brieftext`, `grussformel`

### Phase 4 - Hintergrundausfuehrung

Ziel:

- UI bleibt waehrend KI-Request reaktionsfaehig

Aufgaben:

- `ai_workers.py` anlegen
- Worker und Signals anbinden
- Ladezustand und Fehleranzeige umsetzen

Abnahme:

- UI friert waehrend eines Requests nicht ein

### Phase 5 - Firmenschreiben Tab

Ziel:

- kompletter Dokumenten-Workflow fuer Firmenschreiben

Aufgaben:

- `firmenschreiben.py` anlegen
- Formular aufbauen
- Nummerngenerierung ueber `fs_numbers.py`
- Speichern und Laden anbinden
- PDF-Export einbauen
- KI-Dialog einbauen

Abnahme:

- Ein Nutzer kann ein Firmenschreiben manuell oder per KI erstellen und exportieren

### Phase 6 - KI Dialog im Firmenschreiben

Ziel:

- schneller KI-Zugriff direkt aus dem Schreibprozess

Aufgaben:

- `ai_text_dialog.py` anlegen
- freies Prompt-Feld
- Vorschau der vier Textbausteine
- Buttons fuer Uebernahme

Abnahme:

- Generierte Inhalte koennen direkt in den Firmenschreiben-Tab uebernommen werden

### Phase 7 - Textassistent Tab

Ziel:

- freier Experimentierbereich fuer KI-Text

Aufgaben:

- `text_assistant.py` anlegen
- Prompt-Feld und Ergebnisbereich bauen
- Buttons fuer Revisionen einbauen
- Uebernahme in Firmenschreiben ermoeglichen

Abnahme:

- Der Nutzer kann ohne starren Formularzwang Texte generieren und uebernehmen

### Phase 8 - MainWindow und Einstellungen

Ziel:

- neue Bereiche sauber in die App einhaengen

Aufgaben:

- `main_window.py` um Tabs erweitern
- Shortcut-Anzahl anpassen
- `settings.py` ausbauen
- Modell und Default-Optionen konfigurierbar machen

Abnahme:

- `Textassistent` und `Firmenschreiben` sind im Hauptfenster erreichbar

### Phase 9 - Haertung und End-to-End-Test

Ziel:

- stabile Gesamtstrecke

Aufgaben:

- manuelle Testfaelle durchgehen
- Fehlertexte verbessern
- Parsing robuster machen
- Uebernahmefluesse pruefen

Abnahme:

- End-to-End-Strecke funktioniert:
  - Prompt
  - Generierung
  - Vorschau
  - Uebernahme
  - Speichern
  - PDF-Export

## Empfohlene Commits

1. `chore: add env setup and ai config scaffold`
2. `feat: add firmenschreiben repository`
3. `feat: add firmenschreiben pdf export`
4. `feat: add nvidia ai text service`
5. `feat: add async ai worker and dialog`
6. `feat: add firmenschreiben tab`
7. `feat: add text assistant tab`
8. `feat: wire tabs and settings`
9. `test: harden ai parsing and e2e flows`

## Testfaelle

- Freier Prompt ohne Kundenauswahl
- Freier Prompt mit Kundenauswahl
- Prompt mit sehr kurzem Input
- Prompt mit Bitte um formellen Stil
- Prompt mit Bitte um kuerzeren Stil
- Uebernahme `Alles uebernehmen`
- Uebernahme `Nur Brieftext uebernehmen`
- Speichern eines neuen Firmenschreibens
- Laden eines gespeicherten Firmenschreibens
- PDF-Export
- fehlende `.env`
- fehlender API-Key
- ungueltiger API-Key
- KI liefert kein parsebares JSON

## Risiken

- Das Modell `minimaxai/minimax-m2.5` ist fuer Textqualitaet plausibel, aber nicht garantiert optimal fuer strikt parsebare strukturierte Antworten.
- Deshalb muss die Antwortvalidierung robust sein.
- Desktop-seitige Secret-Nutzung ueber `.env` ist fuer lokalen Einsatz okay, aber kein spaeteres Mehrnutzer-Sicherheitsmodell.

## Abnahmekriterien

- Ein freier Prompt reicht fuer die Generierung aus.
- Optionaler Kontext verbessert die Ausgabe, ist aber nie Pflicht.
- Die App arbeitet intern mit den vier Textfeldern.
- Die Inhalte sind immer vor Uebernahme editierbar.
- `Firmenschreiben` kann gespeichert und als PDF exportiert werden.
- Der API-Key liegt nicht im Quellcode und nicht in der Datenbank.

## Spaetere Erweiterungen

- Archiv fuer Firmenschreiben
- Vorlagen fuer haeufige Schreibanlaesse
- Prompt-Historie
- Favorisierte Modelle
- automatische Stilvorschlaege
- strukturierte Logging-Ansicht fuer KI-Fehler
