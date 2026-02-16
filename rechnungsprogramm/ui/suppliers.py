from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFileDialog, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from db.database import Database
from db.repos.supplier_repo import SupplierRepo
from models.supplier import Supplier
from ui.widgets import FormCard, confirm_delete, show_success, show_error
from utils.paths import get_logos_dir

import shutil
from pathlib import Path


class SuppliersTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.repo = SupplierRepo(db)
        self.current_supplier: Supplier | None = None
        self.logo_file_path: str | None = None

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Linke Seite: Liste
        left = QWidget()
        left_layout = QVBoxLayout(left)

        header_layout = QHBoxLayout()
        title = QLabel("Rechnungssteller")
        title.setProperty("cssClass", "heading")
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_new = QPushButton("+ Neu")
        btn_new.setProperty("cssClass", "primary")
        btn_new.clicked.connect(self.on_new)
        header_layout.addWidget(btn_new)
        left_layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Firma", "Inhaber", "Ort"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_table_double_click)
        left_layout.addWidget(self.table)

        # Linke Seite: Formular
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_widget = QWidget()
        self.form_layout = QVBoxLayout(left_widget)
        self.form_layout.setContentsMargins(16, 16, 16, 16)

        form_title = QLabel("Details")
        form_title.setProperty("cssClass", "subheading")
        self.form_layout.addWidget(form_title)

        # Firmeninfo
        card1 = FormCard("Firmendaten")
        self.inp_firma = QLineEdit()
        self.inp_inhaber = QLineEdit()
        card1.add_field("Firma *", self.inp_firma)
        card1.add_field("Inhaber", self.inp_inhaber)
        self.form_layout.addWidget(card1)

        # Adresse
        card2 = FormCard("Adresse")
        self.inp_strasse = QLineEdit()
        self.inp_plz = QLineEdit()
        self.inp_plz.setMaximumWidth(80)
        self.inp_ort = QLineEdit()
        self.inp_postfach = QLineEdit()
        card2.add_field("Straße", self.inp_strasse)
        plz_ort = QHBoxLayout()
        plz_ort.addWidget(self.inp_plz)
        plz_ort.addWidget(self.inp_ort)
        plz_widget = QWidget()
        plz_widget.setLayout(plz_ort)
        card2.add_field("PLZ / Ort", plz_widget)
        card2.add_field("Postfach", self.inp_postfach)
        self.form_layout.addWidget(card2)

        # Kontakt
        card3 = FormCard("Kontakt")
        self.inp_telefon = QLineEdit()
        self.inp_telefon2 = QLineEdit()
        self.inp_mobil = QLineEdit()
        self.inp_telefax = QLineEdit()
        self.inp_email = QLineEdit()
        self.inp_web = QLineEdit()
        card3.add_field("Telefon", self.inp_telefon)
        card3.add_field("Telefon 2", self.inp_telefon2)
        card3.add_field("Mobil", self.inp_mobil)
        card3.add_field("Telefax", self.inp_telefax)
        card3.add_field("E-Mail", self.inp_email)
        card3.add_field("Webseite", self.inp_web)
        self.form_layout.addWidget(card3)

        # Steuerdaten
        card4 = FormCard("Steuerdaten & Bank")
        self.inp_steuernr = QLineEdit()
        self.inp_ustid = QLineEdit()
        self.inp_bank = QLineEdit()
        self.inp_iban = QLineEdit()
        self.inp_bic = QLineEdit()
        card4.add_field("Steuernummer", self.inp_steuernr)
        card4.add_field("USt-IdNr.", self.inp_ustid)
        card4.add_field("Kreditinstitut", self.inp_bank)
        card4.add_field("IBAN", self.inp_iban)
        card4.add_field("BIC", self.inp_bic)
        self.form_layout.addWidget(card4)

        # Logo
        card5 = FormCard("Logo")
        self.logo_preview = QLabel("Kein Logo")
        self.logo_preview.setFixedHeight(80)
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card5.add_row(self.logo_preview)
        btn_logo = QPushButton("Logo auswählen...")
        btn_logo.clicked.connect(self._select_logo)
        card5.add_row(btn_logo)
        self.form_layout.addWidget(card5)

        # Dankessatz
        card6 = FormCard("Dankessatz")
        self.inp_dankessatz = QTextEdit()
        self.inp_dankessatz.setMaximumHeight(60)
        card6.add_row(self.inp_dankessatz)
        self.form_layout.addWidget(card6)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Speichern")
        btn_save.setProperty("cssClass", "primary")
        btn_save.clicked.connect(self.on_save)
        btn_delete = QPushButton("Löschen")
        btn_delete.setProperty("cssClass", "danger")
        btn_delete.clicked.connect(self._on_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_save)
        self.form_layout.addLayout(btn_layout)

        self.form_layout.addStretch()

        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)
        splitter.addWidget(left)
        splitter.setSizes([500, 400])

        self._load_table()

    def _load_table(self):
        suppliers = self.repo.get_all()
        self.table.setRowCount(len(suppliers))
        for row, s in enumerate(suppliers):
            self.table.setItem(row, 0, QTableWidgetItem(s.firma))
            self.table.setItem(row, 1, QTableWidgetItem(s.inhaber or ""))
            self.table.setItem(row, 2, QTableWidgetItem(s.ort or ""))
            # Store ID in first column's data
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, s.id)

    def _on_table_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            supplier_id = item.data(Qt.ItemDataRole.UserRole)
            supplier = self.repo.get_by_id(supplier_id)
            if supplier:
                self._load_form(supplier)

    def _load_form(self, s: Supplier):
        self.current_supplier = s
        self.inp_firma.setText(s.firma or "")
        self.inp_inhaber.setText(s.inhaber or "")
        self.inp_strasse.setText(s.strasse or "")
        self.inp_plz.setText(s.plz or "")
        self.inp_ort.setText(s.ort or "")
        self.inp_postfach.setText(s.postfach or "")
        self.inp_telefon.setText(s.telefon or "")
        self.inp_telefon2.setText(s.telefon2 or "")
        self.inp_mobil.setText(s.mobil or "")
        self.inp_telefax.setText(s.telefax or "")
        self.inp_email.setText(s.email or "")
        self.inp_web.setText(s.web or "")
        self.inp_steuernr.setText(s.steuernr or "")
        self.inp_ustid.setText(s.ustid or "")
        self.inp_bank.setText(s.bank or "")
        self.inp_iban.setText(s.iban or "")
        self.inp_bic.setText(s.bic or "")
        self.inp_dankessatz.setPlainText(s.dankessatz or "")
        self.logo_file_path = s.logo_path
        self._update_logo_preview()

    def _clear_form(self):
        self.current_supplier = None
        self.logo_file_path = None
        for inp in [
            self.inp_firma, self.inp_inhaber, self.inp_strasse, self.inp_plz,
            self.inp_ort, self.inp_postfach, self.inp_telefon, self.inp_telefon2,
            self.inp_mobil, self.inp_telefax, self.inp_email, self.inp_web,
            self.inp_steuernr, self.inp_ustid, self.inp_bank, self.inp_iban, self.inp_bic,
        ]:
            inp.clear()
        self.inp_dankessatz.setPlainText("Vielen Dank für Ihren Auftrag!")
        self.logo_preview.setText("Kein Logo")
        self.logo_preview.setPixmap(QPixmap())

    def _read_form(self) -> Supplier:
        s = self.current_supplier or Supplier()
        s.firma = self.inp_firma.text().strip()
        s.inhaber = self.inp_inhaber.text().strip() or None
        s.strasse = self.inp_strasse.text().strip() or None
        s.plz = self.inp_plz.text().strip() or None
        s.ort = self.inp_ort.text().strip() or None
        s.postfach = self.inp_postfach.text().strip() or None
        s.telefon = self.inp_telefon.text().strip() or None
        s.telefon2 = self.inp_telefon2.text().strip() or None
        s.mobil = self.inp_mobil.text().strip() or None
        s.telefax = self.inp_telefax.text().strip() or None
        s.email = self.inp_email.text().strip() or None
        s.web = self.inp_web.text().strip() or None
        s.steuernr = self.inp_steuernr.text().strip() or None
        s.ustid = self.inp_ustid.text().strip() or None
        s.bank = self.inp_bank.text().strip() or None
        s.iban = self.inp_iban.text().strip() or None
        s.bic = self.inp_bic.text().strip() or None
        s.dankessatz = self.inp_dankessatz.toPlainText().strip()
        s.logo_path = self.logo_file_path
        return s

    def _select_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg)"
        )
        if path:
            file_path = Path(path)
            if file_path.stat().st_size > 2 * 1024 * 1024:
                show_error(self, "Logo darf maximal 2 MB groß sein.")
                return
            self.logo_file_path = path
            self._update_logo_preview()

    def _update_logo_preview(self):
        if self.logo_file_path:
            pixmap = QPixmap(self.logo_file_path)
            if not pixmap.isNull():
                self.logo_preview.setPixmap(
                    pixmap.scaledToHeight(70, Qt.TransformationMode.SmoothTransformation)
                )
                return
        self.logo_preview.setText("Kein Logo")

    def _save_logo(self, supplier_id: int) -> str | None:
        if not self.logo_file_path:
            return None
        src = Path(self.logo_file_path)
        if not src.exists():
            return self.logo_file_path  # Already saved
        logos_dir = get_logos_dir()
        dest = logos_dir / f"{supplier_id}{src.suffix}"
        if src != dest:
            shutil.copy2(str(src), str(dest))
        return str(dest)

    def on_new(self):
        self._clear_form()
        self.inp_firma.setFocus()

    def on_save(self):
        if not self.inp_firma.text().strip():
            show_error(self, "Firma ist ein Pflichtfeld.")
            return

        s = self._read_form()

        if s.id:
            s.logo_path = self._save_logo(s.id)
            self.repo.update(s)
            show_success(self, "Rechnungssteller aktualisiert.")
        else:
            new_id = self.repo.create(s)
            s.id = new_id
            s.logo_path = self._save_logo(new_id)
            if s.logo_path:
                self.repo.update(s)
            show_success(self, "Rechnungssteller angelegt.")
            self.current_supplier = s

        self._load_table()

    def _on_delete(self):
        if not self.current_supplier or not self.current_supplier.id:
            return
        if confirm_delete(self, f'"{self.current_supplier.firma}"'):
            self.repo.delete(self.current_supplier.id)
            self._clear_form()
            self._load_table()
            show_success(self, "Rechnungssteller gelöscht.")
