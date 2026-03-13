from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QScrollArea, QComboBox, QTextEdit,
    QDialog, QFileDialog, QDialogButtonBox, QProgressDialog,
)
from PySide6.QtCore import Qt

from db.database import Database
from db.repos.customer_repo import CustomerRepo
from models.customer import Customer
from ui.widgets import (
    FormCard, SearchBar, confirm_delete, show_success, show_error,
    create_anrede_combo,
)


# ---------------------------------------------------------------------------
# Import-Vorschau-Dialog
# ---------------------------------------------------------------------------

class _ImportPreviewDialog(QDialog):
    """Zeigt geparste Kunden-DatensÃ¤tze zur Kontrolle vor dem Import."""

    HEADERS = ["Name / Firma", "StraÃŸe", "PLZ", "Ort", "Notizen (Objekt+TÃ¤tigkeiten)"]

    def __init__(self, customers: list[Customer], parent=None):
        super().__init__(parent)
        self.customers = customers
        self.setWindowTitle("Kunden-Import â€“ Vorschau")
        self.setMinimumSize(900, 520)

        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>{len(customers)} DatensÃ¤tze</b> wurden aus der Datei gelesen. "
            'Bitte die Vorschau prÃ¼fen, dann auf "Importieren" klicken.'
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(len(customers), len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        for row, c in enumerate(customers):
            name = c.firma or f"{c.vorname} {c.nachname}".strip() or "â€“"
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(c.strasse or ""))
            self.table.setItem(row, 2, QTableWidgetItem(c.plz or ""))
            self.table.setItem(row, 3, QTableWidgetItem(c.ort or ""))
            self.table.setItem(row, 4, QTableWidgetItem(c.notizen or ""))

        layout.addWidget(self.table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            f"Importieren ({len(customers)})"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


# ---------------------------------------------------------------------------
# Kunden-Tab
# ---------------------------------------------------------------------------

class CustomersTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.repo = CustomerRepo(db)
        self.current_customer: Customer | None = None

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Linke Seite: Liste
        left = QWidget()
        left_layout = QVBoxLayout(left)

        header_layout = QHBoxLayout()
        title = QLabel("Kunden")
        title.setProperty("cssClass", "heading")
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_import = QPushButton("â†‘ Import")
        btn_import.setToolTip("Kunden aus Excel/LibreOffice/CSV importieren")
        btn_import.clicked.connect(self._on_import)
        header_layout.addWidget(btn_import)

        btn_new = QPushButton("+ Neu")
        btn_new.setProperty("cssClass", "primary")
        btn_new.clicked.connect(self.on_new)
        header_layout.addWidget(btn_new)
        left_layout.addLayout(header_layout)

        self.search_bar = SearchBar("Kunden suchen (Name, Firma, Ort)...")
        self.search_bar.search_input.textChanged.connect(self._on_search_changed)
        left_layout.addWidget(self.search_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Firma", "Ort", "Telefon"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_table_double_click)
        left_layout.addWidget(self.table)

        # Rechte Seite: Formular
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_widget = QWidget()
        form_layout = QVBoxLayout(left_widget)
        form_layout.setContentsMargins(16, 16, 16, 16)

        form_title = QLabel("Details")
        form_title.setProperty("cssClass", "subheading")
        form_layout.addWidget(form_title)

        card1 = FormCard("PersÃ¶nliche Daten")
        self.inp_anrede = create_anrede_combo()
        self.inp_titel = QLineEdit()
        self.inp_vorname = QLineEdit()
        self.inp_nachname = QLineEdit()
        self.inp_firma = QLineEdit()
        card1.add_field("Anrede", self.inp_anrede)
        card1.add_field("Titel", self.inp_titel)
        card1.add_field("Vorname", self.inp_vorname)
        card1.add_field("Nachname", self.inp_nachname)
        card1.add_field("Firma", self.inp_firma)
        form_layout.addWidget(card1)

        card2 = FormCard("Adresse")
        self.inp_strasse = QLineEdit()
        self.inp_plz = QLineEdit()
        self.inp_plz.setMaximumWidth(80)
        self.inp_ort = QLineEdit()
        card2.add_field("StraÃŸe", self.inp_strasse)
        plz_ort = QHBoxLayout()
        plz_ort.addWidget(self.inp_plz)
        plz_ort.addWidget(self.inp_ort)
        plz_widget = QWidget()
        plz_widget.setLayout(plz_ort)
        card2.add_field("PLZ / Ort", plz_widget)
        form_layout.addWidget(card2)

        card3 = FormCard("Kontakt")
        self.inp_email = QLineEdit()
        self.inp_telefon = QLineEdit()
        card3.add_field("E-Mail", self.inp_email)
        card3.add_field("Telefon", self.inp_telefon)
        form_layout.addWidget(card3)

        card4 = FormCard("Notizen (Objekt + TÃ¤tigkeiten)")
        self.inp_notizen = QTextEdit()
        self.inp_notizen.setMaximumHeight(120)
        self.inp_notizen.setPlaceholderText("z. B. Musterstr. 1 - Dacharbeiten, Fassade")
        card4.add_row(self.inp_notizen)
        form_layout.addWidget(card4)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Speichern")
        btn_save.setProperty("cssClass", "primary")
        btn_save.clicked.connect(self.on_save)
        btn_delete = QPushButton("LÃ¶schen")
        btn_delete.setProperty("cssClass", "danger")
        btn_delete.clicked.connect(self._on_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_save)
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()

        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)
        splitter.addWidget(left)
        splitter.setSizes([450, 450])

        self._load_table()

    # ------------------------------------------------------------------
    # Tabelle
    # ------------------------------------------------------------------

    def _load_table(self, customers: list[Customer] | None = None):
        if customers is None:
            customers = self.repo.get_all()
        self.table.setRowCount(len(customers))
        for row, c in enumerate(customers):
            name_item = QTableWidgetItem(f"{c.vorname} {c.nachname}")
            name_item.setData(Qt.ItemDataRole.UserRole, c.id)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(c.firma or ""))
            self.table.setItem(row, 2, QTableWidgetItem(c.ort or ""))
            self.table.setItem(row, 3, QTableWidgetItem(c.telefon or ""))

    def _on_search_changed(self, text: str):
        if text.strip():
            results = self.repo.search(text.strip())
        else:
            results = self.repo.get_all()
        self._load_table(results)

    def _on_table_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            customer_id = item.data(Qt.ItemDataRole.UserRole)
            customer = self.repo.get_by_id(customer_id)
            if customer:
                self._load_form(customer)

    # ------------------------------------------------------------------
    # Formular
    # ------------------------------------------------------------------

    def _load_form(self, c: Customer):
        self.current_customer = c
        idx = self.inp_anrede.findText(c.anrede or "")
        self.inp_anrede.setCurrentIndex(max(0, idx))
        self.inp_titel.setText(c.titel or "")
        self.inp_vorname.setText(c.vorname or "")
        self.inp_nachname.setText(c.nachname or "")
        self.inp_firma.setText(c.firma or "")
        self.inp_strasse.setText(c.strasse or "")
        self.inp_plz.setText(c.plz or "")
        self.inp_ort.setText(c.ort or "")
        self.inp_email.setText(c.email or "")
        self.inp_telefon.setText(c.telefon or "")
        self.inp_notizen.setPlainText(c.notizen or "")

    def _clear_form(self):
        self.current_customer = None
        self.inp_anrede.setCurrentIndex(0)
        for inp in [
            self.inp_titel, self.inp_vorname, self.inp_nachname, self.inp_firma,
            self.inp_strasse, self.inp_plz, self.inp_ort, self.inp_email, self.inp_telefon,
        ]:
            inp.clear()
        self.inp_notizen.clear()

    def _read_form(self) -> Customer:
        c = self.current_customer or Customer()
        c.anrede = self.inp_anrede.currentText()
        c.titel = self.inp_titel.text().strip() or None
        c.vorname = self.inp_vorname.text().strip()
        c.nachname = self.inp_nachname.text().strip()
        c.firma = self.inp_firma.text().strip() or None
        c.strasse = self.inp_strasse.text().strip() or None
        c.plz = self.inp_plz.text().strip() or None
        c.ort = self.inp_ort.text().strip() or None
        c.email = self.inp_email.text().strip() or None
        c.telefon = self.inp_telefon.text().strip() or None
        c.notizen = self.inp_notizen.toPlainText().strip() or None
        return c

    # ------------------------------------------------------------------
    # Aktionen
    # ------------------------------------------------------------------

    def on_new(self):
        self._clear_form()
        self.inp_vorname.setFocus()

    def on_save(self):
        c = self._read_form()
        if c.id:
            self.repo.update(c)
            show_success(self, "Kunde aktualisiert.")
        else:
            c.id = self.repo.create(c)
            self.current_customer = c
            show_success(self, "Kunde angelegt.")
        self._load_table()

    def _on_delete(self):
        if not self.current_customer or not self.current_customer.id:
            return
        if confirm_delete(self, f'"{self.current_customer.full_name}"'):
            self.repo.delete(self.current_customer.id)
            self._clear_form()
            self._load_table()
            show_success(self, "Kunde gelÃ¶scht.")

    def on_search(self):
        self.search_bar.search_input.setFocus()

    # ------------------------------------------------------------------
    # Kunden-Import
    # ------------------------------------------------------------------

    def _on_import(self):
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Kundenliste Ã¶ffnen",
            "",
            "Tabellen (*.xlsx *.xlsm *.ods *.csv *.tsv);;Alle Dateien (*)",
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            from utils.customer_import import read_file
            customers = read_file(path)
        except ImportError as e:
            show_error(self, str(e))
            return
        except Exception as e:
            show_error(self, f"Datei konnte nicht gelesen werden:\n{e}")
            return

        if not customers:
            show_error(self, "Es wurden keine DatensÃ¤tze in der Datei gefunden.")
            return

        dlg = _ImportPreviewDialog(customers, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        progress = QProgressDialog("Importiere Kundenâ€¦", None, 0, len(customers), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        imported = 0
        errors = 0
        for i, c in enumerate(customers):
            progress.setValue(i)
            try:
                self.repo.create(c)
                imported += 1
            except Exception:
                errors += 1

        progress.setValue(len(customers))
        self._load_table()

        msg = f"{imported} Kunden erfolgreich importiert."
        if errors:
            msg += f"\n{errors} DatensÃ¤tze konnten nicht importiert werden."
        show_success(self, msg)
