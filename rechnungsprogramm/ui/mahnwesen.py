import os
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QRadioButton, QButtonGroup, QTextEdit, QGroupBox, QSplitter,
    QFrame,
)
from PySide6.QtCore import Qt, QDate

from db.database import Database
from db.repos.invoice_repo import InvoiceRepo
from db.repos.customer_repo import CustomerRepo
from db.repos.supplier_repo import SupplierRepo
from models.invoice import Invoice
from ui.widgets import (
    SearchBar, StatusBadge, show_error, create_date_edit,
)
from export.mahnung_pdf_generator import generate_mahnung_pdf, get_mahnung_template_text


class MahnwesenTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.invoice_repo = InvoiceRepo(db)
        self.customer_repo = CustomerRepo(db)
        self.supplier_repo = SupplierRepo(db)
        self._selected_invoice: Invoice | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Mahnwesen")
        title.setProperty("cssClass", "heading")
        header.addWidget(title)
        header.addStretch()

        self.filter_status = QComboBox()
        self.filter_status.addItem("Alle Status", None)
        self.filter_status.addItem("Entwurf", "entwurf")
        self.filter_status.addItem("Versendet", "versendet")
        self.filter_status.addItem("Bezahlt", "bezahlt")
        self.filter_status.currentIndexChanged.connect(self._load_table)
        header.addWidget(self.filter_status)
        layout.addLayout(header)

        # Suche
        self.search_bar = SearchBar("Suche (Rechnungsnr., Kunde, Betreff)...")
        self.search_bar.search_input.textChanged.connect(self._load_table)
        layout.addWidget(self.search_bar)

        # Splitter: Tabelle oben, Formular unten
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, 1)

        # === Oberer Teil: Rechnungstabelle ===
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Rechnungsnr.", "Datum", "Kunde", "Betreff", "Brutto", "Status",
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_widget)

        # === Unterer Teil: Formular ===
        form_widget = QWidget()
        form_layout = QHBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 8, 0, 0)
        form_layout.setSpacing(16)

        # Linke Seite: Typ + Datum
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_widget.setFixedWidth(220)

        # Typ-Auswahl
        typ_group = QGroupBox("Typ")
        typ_layout = QVBoxLayout(typ_group)
        self.radio_erinnerung = QRadioButton("Zahlungserinnerung")
        self.radio_mahnung2 = QRadioButton("2. Mahnung")
        self.radio_erinnerung.setChecked(True)
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_erinnerung)
        self.btn_group.addButton(self.radio_mahnung2)
        self.btn_group.buttonClicked.connect(self._on_type_changed)
        typ_layout.addWidget(self.radio_erinnerung)
        typ_layout.addWidget(self.radio_mahnung2)
        left_layout.addWidget(typ_group)

        # Datum
        datum_group = QGroupBox("Datum")
        datum_layout = QVBoxLayout(datum_group)
        self.date_edit = create_date_edit(default_today=True)
        datum_layout.addWidget(self.date_edit)
        left_layout.addWidget(datum_group)

        left_layout.addStretch()
        form_layout.addWidget(left_widget)

        # Rechte Seite: Text + Button
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        text_label = QLabel("Text (bearbeitbar):")
        text_label.setProperty("cssClass", "secondary")
        right_layout.addWidget(text_label)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setPlaceholderText(
            "Bitte zuerst eine Rechnung aus der Liste auswählen..."
        )
        self.text_edit.setEnabled(False)
        right_layout.addWidget(self.text_edit, 1)

        self.btn_export = QPushButton("PDF exportieren")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export_pdf)
        right_layout.addWidget(self.btn_export)

        form_layout.addWidget(right_widget, 1)
        splitter.addWidget(form_widget)

        splitter.setSizes([350, 300])

    def showEvent(self, event):
        super().showEvent(event)
        self._load_table()

    def _load_table(self, *_):
        query = self.search_bar.text.strip()
        if query:
            invoices = self.invoice_repo.search(query)
        else:
            invoices = self.invoice_repo.get_all()

        status_filter = self.filter_status.currentData()
        if status_filter:
            invoices = [i for i in invoices if i.status == status_filter]

        self.table.setRowCount(len(invoices))
        for row, inv in enumerate(invoices):
            nr_item = QTableWidgetItem(inv.rechnungsnr)
            nr_item.setData(Qt.ItemDataRole.UserRole, inv.id)
            self.table.setItem(row, 0, nr_item)

            datum_str = ""
            if inv.datum:
                if isinstance(inv.datum, str):
                    parts = inv.datum.split("-")
                    if len(parts) == 3:
                        datum_str = f"{parts[2]}.{parts[1]}.{parts[0]}"
                else:
                    datum_str = inv.datum.strftime("%d.%m.%Y")
            self.table.setItem(row, 1, QTableWidgetItem(datum_str))

            customer = self.customer_repo.get_by_id(inv.customer_id)
            kunde_name = customer.full_name if customer else f"ID {inv.customer_id}"
            self.table.setItem(row, 2, QTableWidgetItem(kunde_name))

            self.table.setItem(row, 3, QTableWidgetItem(inv.betreff or ""))

            brutto = inv.brutto or 0
            brutto_str = f"{brutto:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
            self.table.setItem(row, 4, QTableWidgetItem(brutto_str))

            badge = StatusBadge(inv.status)
            self.table.setCellWidget(row, 5, badge)

    def _on_table_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self._selected_invoice = None
            self.text_edit.setEnabled(False)
            self.btn_export.setEnabled(False)
            return

        row = rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return

        invoice_id = item.data(Qt.ItemDataRole.UserRole)
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if invoice:
            self._selected_invoice = invoice
            self._populate_form(invoice)

    def load_invoice(self, invoice: Invoice):
        """Öffentliche Methode: Rechnung in Tabelle selektieren und Formular befüllen."""
        self._load_table()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == invoice.id:
                self.table.setCurrentCell(row, 0)
                break
        else:
            # Rechnung nicht in aktuell gefilterter Liste – Filter zurücksetzen
            self.filter_status.setCurrentIndex(0)
            self._load_table()
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == invoice.id:
                    self.table.setCurrentCell(row, 0)
                    break

        self._selected_invoice = invoice
        self._populate_form(invoice)

    def _populate_form(self, invoice: Invoice):
        self.date_edit.setDate(QDate.currentDate())
        self.text_edit.setEnabled(True)
        self.btn_export.setEnabled(True)
        self._generate_and_fill_template(invoice)

    def _on_type_changed(self, *_):
        if self._selected_invoice:
            self._generate_and_fill_template(self._selected_invoice)

    def _generate_and_fill_template(self, invoice: Invoice):
        customer = self.customer_repo.get_by_id(invoice.customer_id)
        if not customer:
            return
        mahnung_typ = (
            "Zahlungserinnerung" if self.radio_erinnerung.isChecked() else "2. Mahnung"
        )
        text = get_mahnung_template_text(mahnung_typ, customer, invoice)
        self.text_edit.setPlainText(text)

    def _on_export_pdf(self):
        if not self._selected_invoice:
            show_error(self, "Bitte zuerst eine Rechnung auswählen.")
            return

        suppliers = self.supplier_repo.get_all()
        if not suppliers:
            show_error(self, "Kein Rechnungssteller vorhanden. Bitte zuerst einen Lieferanten anlegen.")
            return

        supplier = suppliers[0]
        customer = self.customer_repo.get_by_id(self._selected_invoice.customer_id)
        if not customer:
            show_error(self, "Kunde nicht gefunden.")
            return

        mahnung_typ = (
            "Zahlungserinnerung" if self.radio_erinnerung.isChecked() else "2. Mahnung"
        )
        qdate = self.date_edit.date()
        mahnung_datum = date(qdate.year(), qdate.month(), qdate.day())
        body_text = self.text_edit.toPlainText()

        try:
            pdf_path = generate_mahnung_pdf(
                invoice=self._selected_invoice,
                supplier=supplier,
                customer=customer,
                mahnung_typ=mahnung_typ,
                mahnung_datum=mahnung_datum,
                body_text=body_text,
            )
            os.startfile(str(pdf_path))
            main_window = self.window()
            if hasattr(main_window, "set_status"):
                main_window.set_status(f"{mahnung_typ} gespeichert: {pdf_path}")
        except Exception as e:
            show_error(self, f"Fehler beim PDF-Export:\n{e}")
