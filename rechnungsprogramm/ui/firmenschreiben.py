from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from db.database import Database
from db.repos.customer_repo import CustomerRepo
from db.repos.fs_repo import FSRepo
from db.repos.supplier_repo import SupplierRepo
from models.firmenschreiben import Firmenschreiben
from ui.ai_text_dialog import AITextDialog
from ui.widgets import FormCard, create_date_edit, show_error, show_success


class FirmenschreibenTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.supplier_repo = SupplierRepo(db)
        self.customer_repo = CustomerRepo(db)
        self.fs_repo = FSRepo(db)
        self.current_fs: Firmenschreiben | None = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        title = QLabel("Firmenschreiben erstellen")
        title.setProperty("cssClass", "heading")
        self.main_layout.addWidget(title)

        subtitle = QLabel(
            "Erstelle freie Anschreiben, speichere Entwuerfe und nutze die KI bei Bedarf "
            "als Formulierungshilfe fuer Betreff, Anrede, Brieftext und Grussformel."
        )
        subtitle.setProperty("cssClass", "secondary")
        subtitle.setWordWrap(True)
        self.main_layout.addWidget(subtitle)

        self._build_kopfdaten()
        self._build_brieftext()
        self._build_liste()
        self._build_buttons()

        self.main_layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_kopfdaten(self):
        card = FormCard("Kopfdaten")

        self.cmb_supplier = QComboBox()
        self.cmb_supplier.currentIndexChanged.connect(self._on_supplier_changed)
        card.add_field("Rechnungssteller", self.cmb_supplier)

        self.lbl_supplier_info = QLabel("")
        self.lbl_supplier_info.setProperty("cssClass", "secondary")
        self.lbl_supplier_info.setWordWrap(True)
        card.add_row(self.lbl_supplier_info)

        self.cmb_customer = QComboBox()
        self.cmb_customer.currentIndexChanged.connect(self._on_customer_changed)
        card.add_field("Empfaenger", self.cmb_customer)

        self.lbl_customer_info = QLabel("")
        self.lbl_customer_info.setProperty("cssClass", "secondary")
        self.lbl_customer_info.setWordWrap(True)
        card.add_row(self.lbl_customer_info)

        nr_layout = QHBoxLayout()
        self.inp_fsnr = QLineEdit()
        self.inp_fsnr.setPlaceholderText("Automatisch")
        self.btn_auto_nr = QPushButton("Auto")
        self.btn_auto_nr.clicked.connect(self._generate_number)
        nr_layout.addWidget(self.inp_fsnr)
        nr_layout.addWidget(self.btn_auto_nr)
        nr_widget = QWidget()
        nr_widget.setLayout(nr_layout)
        card.add_field("Schreiben-Nr.", nr_widget)

        self.inp_datum = create_date_edit()
        self.inp_datum.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        card.add_field("Datum *", self.inp_datum)

        self.inp_betreff = QLineEdit()
        card.add_field("Betreff", self.inp_betreff)

        self.inp_anrede = QLineEdit()
        self.inp_anrede.setPlaceholderText("Sehr geehrte Damen und Herren,")
        card.add_field("Anrede", self.inp_anrede)

        self.inp_grussformel = QLineEdit()
        self.inp_grussformel.setText("Mit freundlichen Gruessen")
        card.add_field("Grussformel", self.inp_grussformel)

        self.cmb_status = QComboBox()
        self.cmb_status.addItem("Entwurf", "entwurf")
        self.cmb_status.addItem("Versendet", "versendet")
        card.add_field("Status", self.cmb_status)

        self.main_layout.addWidget(card)

    def _build_brieftext(self):
        card = FormCard("Brieftext")

        info = QLabel(
            "Du kannst direkt schreiben oder dir ueber den KI-Dialog einen editierbaren Entwurf erstellen lassen."
        )
        info.setProperty("cssClass", "secondary")
        info.setWordWrap(True)
        card.add_row(info)

        action_layout = QHBoxLayout()
        self.btn_ai = QPushButton("Mit KI formulieren")
        self.btn_ai.setToolTip("Oeffnet den KI-Dialog mit optionalem Kunden-, Firmen- und Entwurfskontext.")
        self.btn_ai.clicked.connect(self._open_ai_dialog)
        action_layout.addWidget(self.btn_ai)
        action_layout.addStretch()
        action_widget = QWidget()
        action_widget.setLayout(action_layout)
        card.add_row(action_widget)

        self.inp_brieftext = QTextEdit()
        self.inp_brieftext.setAcceptRichText(False)
        self.inp_brieftext.setMinimumHeight(220)
        self.inp_brieftext.setPlaceholderText("Text des Schreibens...")
        card.add_row(self.inp_brieftext)

        self.main_layout.addWidget(card)

    def _build_liste(self):
        card = FormCard("Gespeicherte Firmenschreiben")

        search_layout = QHBoxLayout()
        self.inp_suche = QLineEdit()
        self.inp_suche.setPlaceholderText("Suche (Nr., Betreff, Empfaenger)...")
        self.inp_suche.textChanged.connect(self._load_table)
        search_layout.addWidget(self.inp_suche)
        search_widget = QWidget()
        search_widget.setLayout(search_layout)
        card.add_row(search_widget)

        self.tbl_liste = QTableWidget()
        self.tbl_liste.setColumnCount(6)
        self.tbl_liste.setHorizontalHeaderLabels(
            ["Nr.", "Datum", "Empfaenger", "Betreff", "Status", "Aktionen"]
        )
        self.tbl_liste.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_liste.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_liste.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_liste.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_liste.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.tbl_liste.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tbl_liste.setColumnWidth(0, 140)
        self.tbl_liste.setColumnWidth(1, 90)
        self.tbl_liste.setColumnWidth(4, 80)
        self.tbl_liste.setColumnWidth(5, 140)
        self.tbl_liste.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_liste.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_liste.verticalHeader().setVisible(False)
        self.tbl_liste.setMinimumHeight(180)
        self.tbl_liste.doubleClicked.connect(self._on_table_double_click)
        card.add_row(self.tbl_liste)

        self.main_layout.addWidget(card)

    def _build_buttons(self):
        from utils.paths import get_fs_base_dir

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Export-Zielordner:"))
        self.lbl_export_path = QLabel(str(get_fs_base_dir()))
        self.lbl_export_path.setProperty("cssClass", "secondary")
        self.lbl_export_path.setWordWrap(True)
        folder_layout.addWidget(self.lbl_export_path, 1)

        btn_folder = QPushButton("Aendern...")
        btn_folder.clicked.connect(self._select_export_folder)
        folder_layout.addWidget(btn_folder)
        self.main_layout.addLayout(folder_layout)

        btn_layout = QHBoxLayout()

        btn_clear = QPushButton("Neues Schreiben")
        btn_clear.clicked.connect(self._clear_form)

        btn_save = QPushButton("Speichern")
        btn_save.setProperty("cssClass", "primary")
        btn_save.clicked.connect(self.on_save)

        btn_pdf = QPushButton("PDF exportieren")
        btn_pdf.clicked.connect(self._export_pdf)

        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_pdf)
        btn_layout.addWidget(btn_save)

        self.main_layout.addLayout(btn_layout)

    def _select_export_folder(self):
        from utils.paths import get_fs_base_dir, set_fs_base_dir

        current = str(get_fs_base_dir())
        folder = QFileDialog.getExistingDirectory(self, "Export-Zielordner waehlen", current)
        if folder:
            set_fs_base_dir(folder)
            self.lbl_export_path.setText(folder)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_contexts()
        self._load_table()

    def refresh_contexts(self):
        self._refresh_dropdowns()

    def _refresh_dropdowns(self):
        current_supplier = self.cmb_supplier.currentData()
        self.cmb_supplier.blockSignals(True)
        self.cmb_supplier.clear()
        self.cmb_supplier.addItem("-- Kein Absender --", None)
        for supplier in self.supplier_repo.get_all():
            self.cmb_supplier.addItem(supplier.firma, supplier.id)
        if current_supplier is not None:
            idx = self.cmb_supplier.findData(current_supplier)
            if idx >= 0:
                self.cmb_supplier.setCurrentIndex(idx)
        self.cmb_supplier.blockSignals(False)

        current_customer = self.cmb_customer.currentData()
        self.cmb_customer.blockSignals(True)
        self.cmb_customer.clear()
        self.cmb_customer.addItem("-- Kein Empfaenger --", None)
        for customer in self.customer_repo.get_all():
            self.cmb_customer.addItem(customer.display_name, customer.id)
        if current_customer is not None:
            idx = self.cmb_customer.findData(current_customer)
            if idx >= 0:
                self.cmb_customer.setCurrentIndex(idx)
        self.cmb_customer.blockSignals(False)

    def _on_supplier_changed(self, index):
        supplier_id = self.cmb_supplier.currentData()
        if supplier_id:
            supplier = self.supplier_repo.get_by_id(supplier_id)
            if supplier:
                info_parts = [
                    part
                    for part in [
                        supplier.strasse,
                        f"{supplier.plz or ''} {supplier.ort or ''}".strip(),
                        supplier.telefon,
                        supplier.email,
                    ]
                    if part
                ]
                self.lbl_supplier_info.setText(" | ".join(info_parts))
                return
        self.lbl_supplier_info.setText("")

    def _on_customer_changed(self, index):
        customer_id = self.cmb_customer.currentData()
        if customer_id:
            customer = self.customer_repo.get_by_id(customer_id)
            if customer:
                info_parts = [
                    part
                    for part in [
                        customer.strasse,
                        f"{customer.plz or ''} {customer.ort or ''}".strip(),
                        customer.telefon,
                    ]
                    if part
                ]
                self.lbl_customer_info.setText(" | ".join(info_parts))
                if not self.inp_anrede.text().strip():
                    self.inp_anrede.setText(self._build_anrede(customer))
                return
        self.lbl_customer_info.setText("")

    def _build_anrede(self, customer) -> str:
        anrede = (customer.anrede or "").strip()
        nachname = (customer.nachname or "").strip()
        titel = (customer.titel or "").strip()

        if not nachname:
            return "Sehr geehrte Damen und Herren,"

        name_teil = f"{titel} {nachname}".strip() if titel else nachname
        if anrede == "Herr":
            return f"Sehr geehrter Herr {name_teil},"
        if anrede == "Frau":
            return f"Sehr geehrte Frau {name_teil},"
        return "Sehr geehrte Damen und Herren,"

    def _generate_number(self):
        from utils.fs_numbers import naechste_fsnr

        selected_date = date(
            self.inp_datum.date().year(),
            self.inp_datum.date().month(),
            self.inp_datum.date().day(),
        )
        self.inp_fsnr.setText(naechste_fsnr(self.db, selected_date))

    def _load_table(self, *_):
        query = self.inp_suche.text().strip()
        entries = self.fs_repo.search(query) if query else self.fs_repo.get_all()

        self.tbl_liste.setRowCount(0)
        for fs in entries:
            row = self.tbl_liste.rowCount()
            self.tbl_liste.insertRow(row)

            customer_name = ""
            if fs.customer_id:
                customer = self.customer_repo.get_by_id(fs.customer_id)
                if customer:
                    customer_name = customer.display_name

            datum_str = fs.datum.strftime("%d.%m.%Y") if isinstance(fs.datum, date) else str(fs.datum or "")
            status_label = "Entwurf" if fs.status == "entwurf" else "Versendet"

            self.tbl_liste.setItem(row, 0, QTableWidgetItem(fs.fsnr))
            self.tbl_liste.setItem(row, 1, QTableWidgetItem(datum_str))
            self.tbl_liste.setItem(row, 2, QTableWidgetItem(customer_name))
            self.tbl_liste.setItem(row, 3, QTableWidgetItem(fs.betreff or ""))
            self.tbl_liste.setItem(row, 4, QTableWidgetItem(status_label))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            btn_laden = QPushButton("Laden")
            btn_laden.setFixedHeight(24)
            btn_laden.clicked.connect(lambda _, current_fs=fs: self._laden_fs(current_fs))
            btn_layout.addWidget(btn_laden)

            btn_pdf = QPushButton("PDF")
            btn_pdf.setFixedHeight(24)
            btn_pdf.clicked.connect(lambda _, current_fs=fs: self._pdf_fs(current_fs))
            btn_layout.addWidget(btn_pdf)

            self.tbl_liste.setCellWidget(row, 5, btn_widget)

        self.tbl_liste.resizeRowsToContents()

    def _on_table_double_click(self, index):
        row = index.row()
        query = self.inp_suche.text().strip()
        entries = self.fs_repo.search(query) if query else self.fs_repo.get_all()
        if 0 <= row < len(entries):
            self._laden_fs(entries[row])

    def _laden_fs(self, fs: Firmenschreiben):
        fs_full = self.fs_repo.get_by_id(fs.id)
        if fs_full:
            self.load_fs(fs_full)

    def _pdf_fs(self, fs: Firmenschreiben):
        fs_full = self.fs_repo.get_by_id(fs.id)
        if fs_full:
            self.load_fs(fs_full)
            self._export_pdf()

    def load_fs(self, fs: Firmenschreiben):
        self.current_fs = fs
        self.refresh_contexts()

        if fs.supplier_id is not None:
            idx = self.cmb_supplier.findData(fs.supplier_id)
            if idx >= 0:
                self.cmb_supplier.setCurrentIndex(idx)

        if fs.customer_id is not None:
            idx = self.cmb_customer.findData(fs.customer_id)
            if idx >= 0:
                self.cmb_customer.setCurrentIndex(idx)

        self.inp_fsnr.setText(fs.fsnr)
        if isinstance(fs.datum, date):
            self.inp_datum.setDate(QDate(fs.datum.year, fs.datum.month, fs.datum.day))
        self.inp_betreff.setText(fs.betreff or "")
        self.inp_anrede.setText(fs.anrede or "")
        self.inp_brieftext.setPlainText(fs.brieftext or "")
        self.inp_grussformel.setText(fs.grussformel or "Mit freundlichen Gruessen")

        idx = self.cmb_status.findData(fs.status)
        if idx >= 0:
            self.cmb_status.setCurrentIndex(idx)

    def _clear_form(self):
        self.current_fs = None
        self.cmb_supplier.setCurrentIndex(0)
        self.cmb_customer.setCurrentIndex(0)
        self.inp_fsnr.clear()
        self.inp_datum.setDate(QDate.currentDate())
        self.inp_betreff.clear()
        self.inp_anrede.clear()
        self.inp_brieftext.clear()
        self.inp_grussformel.setText("Mit freundlichen Gruessen")
        self.cmb_status.setCurrentIndex(0)

    def _read_fs(self) -> Firmenschreiben | None:
        brieftext = self.inp_brieftext.toPlainText().strip()
        if not brieftext:
            show_error(self, "Bitte geben Sie einen Brieftext ein.")
            return None

        fsnr = self.inp_fsnr.text().strip()
        if not fsnr:
            self._generate_number()
            fsnr = self.inp_fsnr.text().strip()

        fs = self.current_fs or Firmenschreiben()
        fs.supplier_id = self.cmb_supplier.currentData()
        fs.customer_id = self.cmb_customer.currentData()
        fs.fsnr = fsnr
        fs.datum = date(
            self.inp_datum.date().year(),
            self.inp_datum.date().month(),
            self.inp_datum.date().day(),
        )
        fs.betreff = self.inp_betreff.text().strip() or None
        fs.anrede = self.inp_anrede.text().strip() or None
        fs.brieftext = brieftext
        fs.grussformel = self.inp_grussformel.text().strip() or "Mit freundlichen Gruessen"
        fs.status = self.cmb_status.currentData() or "entwurf"
        return fs

    def on_new(self):
        self._clear_form()

    def on_save(self):
        fs = self._read_fs()
        if not fs:
            return

        if fs.id:
            self.fs_repo.update(fs)
            show_success(self, f"Firmenschreiben {fs.fsnr} aktualisiert.")
        else:
            fs.id = self.fs_repo.create(fs)
            self.current_fs = fs
            show_success(self, f"Firmenschreiben {fs.fsnr} gespeichert.")

        self._load_table()
        main_window = self.window()
        if hasattr(main_window, "set_status"):
            main_window.set_status(f"Firmenschreiben {fs.fsnr} gespeichert.")

    def _export_pdf(self):
        fs = self._read_fs()
        if not fs:
            return

        if fs.id:
            self.fs_repo.update(fs)
        else:
            fs.id = self.fs_repo.create(fs)
            self.current_fs = fs

        try:
            from export.fs_pdf_generator import generate_fs_pdf

            supplier = self.supplier_repo.get_by_id(fs.supplier_id) if fs.supplier_id else None
            customer = self.customer_repo.get_by_id(fs.customer_id) if fs.customer_id else None
            pdf_path = generate_fs_pdf(fs, supplier, customer)

            self.fs_repo.update_pdf_path(fs.id, str(pdf_path))
            fs.pdf_path = str(pdf_path)

            if fs.status == "entwurf":
                self.fs_repo.update_status(fs.id, "versendet")
                fs.status = "versendet"
                idx = self.cmb_status.findData("versendet")
                if idx >= 0:
                    self.cmb_status.setCurrentIndex(idx)

            self._load_table()
            show_success(self, f"PDF exportiert: {pdf_path}")

            import os
            os.startfile(str(pdf_path))

            main_window = self.window()
            if hasattr(main_window, "set_status"):
                main_window.set_status(f"Firmenschreiben exportiert: {pdf_path}")
        except Exception as exc:
            show_error(self, f"PDF-Export fehlgeschlagen: {exc}")

    def on_search(self):
        self.inp_suche.setFocus()

    def apply_generated_text(self, data: dict[str, str]):
        betreff = (data.get("betreff") or "").strip()
        anrede = (data.get("anrede") or "").strip()
        brieftext = (data.get("brieftext") or "").strip()
        grussformel = (data.get("grussformel") or "").strip()

        if betreff:
            self.inp_betreff.setText(betreff)
        if anrede:
            self.inp_anrede.setText(anrede)
        if brieftext:
            self.inp_brieftext.setPlainText(brieftext)
        if grussformel:
            self.inp_grussformel.setText(grussformel)

    def _open_ai_dialog(self):
        dialog = AITextDialog(self)
        dialog.set_context(
            supplier=self.supplier_repo.get_by_id(self.cmb_supplier.currentData())
            if self.cmb_supplier.currentData() else None,
            customer=self.customer_repo.get_by_id(self.cmb_customer.currentData())
            if self.cmb_customer.currentData() else None,
            draft={
                "betreff": self.inp_betreff.text().strip(),
                "anrede": self.inp_anrede.text().strip(),
                "brieftext": self.inp_brieftext.toPlainText().strip(),
                "grussformel": self.inp_grussformel.text().strip(),
            },
        )

        if dialog.exec():
            data = dialog.get_generated_data()
            if dialog.get_accept_mode() == "body_only":
                body = (data.get("brieftext") or "").strip()
                if body:
                    self.inp_brieftext.setPlainText(body)
                    status_message = "KI-Brieftext in Firmenschreiben uebernommen."
                else:
                    status_message = "Kein KI-Brieftext uebernommen."
            else:
                self.apply_generated_text(data)
                status_message = "KI-Entwurf in Firmenschreiben uebernommen."

            main_window = self.window()
            if hasattr(main_window, "set_status"):
                main_window.set_status(status_message)
