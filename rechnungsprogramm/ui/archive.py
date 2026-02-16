import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMenu,
)
from PySide6.QtCore import Qt

from db.database import Database
from db.repos.invoice_repo import InvoiceRepo
from db.repos.customer_repo import CustomerRepo
from models.invoice import Invoice
from models.enums import InvoiceStatus
from ui.widgets import SearchBar, StatusBadge, confirm_delete, show_success, show_error


class ArchiveTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.invoice_repo = InvoiceRepo(db)
        self.customer_repo = CustomerRepo(db)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QHBoxLayout()
        title = QLabel("Rechnungsarchiv")
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
        self.search_bar.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_bar)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Rechnungsnr.", "Datum", "Kunde", "Betreff", "Brutto", "Status", "Aktionen"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table)

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
            # Rechnungsnr
            nr_item = QTableWidgetItem(inv.rechnungsnr)
            nr_item.setData(Qt.ItemDataRole.UserRole, inv.id)
            self.table.setItem(row, 0, nr_item)

            # Datum
            datum_str = ""
            if inv.datum:
                if isinstance(inv.datum, str):
                    parts = inv.datum.split("-")
                    if len(parts) == 3:
                        datum_str = f"{parts[2]}.{parts[1]}.{parts[0]}"
                else:
                    datum_str = inv.datum.strftime("%d.%m.%Y")
            self.table.setItem(row, 1, QTableWidgetItem(datum_str))

            # Kunde
            customer = self.customer_repo.get_by_id(inv.customer_id)
            kunde_name = customer.full_name if customer else f"ID {inv.customer_id}"
            self.table.setItem(row, 2, QTableWidgetItem(kunde_name))

            # Betreff
            self.table.setItem(row, 3, QTableWidgetItem(inv.betreff or ""))

            # Brutto
            brutto = inv.brutto or 0
            brutto_str = f"{brutto:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
            self.table.setItem(row, 4, QTableWidgetItem(brutto_str))

            # Status Badge
            badge = StatusBadge(inv.status)
            self.table.setCellWidget(row, 5, badge)

            # Aktionen
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            if inv.pdf_path:
                btn_pdf = QPushButton("PDF")
                btn_pdf.setFixedWidth(50)
                btn_pdf.clicked.connect(lambda _, p=inv.pdf_path: self._open_pdf(p))
                actions_layout.addWidget(btn_pdf)

            btn_status = QPushButton("Status")
            btn_status.setFixedWidth(50)
            btn_status.clicked.connect(lambda _, iid=inv.id, s=inv.status: self._cycle_status(iid, s))
            actions_layout.addWidget(btn_status)

            self.table.setCellWidget(row, 6, actions)

    def _on_search(self, text: str):
        self._load_table()

    def _on_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            invoice_id = item.data(Qt.ItemDataRole.UserRole)
            invoice = self.invoice_repo.get_by_id(invoice_id)
            if invoice:
                self._open_invoice(invoice)

    def _open_invoice(self, invoice: Invoice):
        # Switch to invoice tab and load invoice
        main_window = self.window()
        if hasattr(main_window, "tabs") and hasattr(main_window, "invoices_tab"):
            main_window.invoices_tab.load_invoice(invoice)
            main_window.tabs.setCurrentWidget(main_window.invoices_tab)

    def _open_pdf(self, path: str):
        if os.path.exists(path):
            os.startfile(path)
        else:
            show_error(self, f"PDF nicht gefunden: {path}")

    def _cycle_status(self, invoice_id: int, current_status: str):
        next_status = {
            "entwurf": "versendet",
            "versendet": "bezahlt",
            "bezahlt": "bezahlt",
        }
        new_status = next_status.get(current_status, current_status)
        if new_status != current_status:
            self.invoice_repo.update_status(invoice_id, new_status)
            self._load_table()

    def _show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        item = self.table.item(row, 0)
        if not item:
            return

        invoice_id = item.data(Qt.ItemDataRole.UserRole)
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            return

        menu = QMenu(self)
        menu.addAction("Bearbeiten", lambda: self._open_invoice(invoice))

        if invoice.pdf_path and os.path.exists(invoice.pdf_path):
            menu.addAction("PDF öffnen", lambda: self._open_pdf(invoice.pdf_path))

        menu.addSeparator()

        if invoice.status != "bezahlt":
            menu.addAction("Als bezahlt markieren",
                           lambda: self._set_status(invoice_id, "bezahlt"))
        if invoice.status == "entwurf":
            menu.addAction("Als versendet markieren",
                           lambda: self._set_status(invoice_id, "versendet"))

        menu.addSeparator()
        menu.addAction("Duplizieren", lambda: self._duplicate(invoice))
        menu.addSeparator()
        menu.addAction("Löschen", lambda: self._delete(invoice_id))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _set_status(self, invoice_id: int, status: str):
        self.invoice_repo.update_status(invoice_id, status)
        self._load_table()

    def _duplicate(self, invoice: Invoice):
        from db.repos.number_repo import NumberRepo
        from datetime import date

        nr_repo = NumberRepo(self.db)
        new_nr = nr_repo.naechste_nummer(date.today().year)

        new_inv = Invoice(
            supplier_id=invoice.supplier_id,
            customer_id=invoice.customer_id,
            rechnungsnr=new_nr,
            datum=date.today(),
            betreff=invoice.betreff,
            objekt_weg=invoice.objekt_weg,
            zahlungsziel=invoice.zahlungsziel,
            rabatt_typ=invoice.rabatt_typ,
            rabatt_wert=invoice.rabatt_wert,
            lohnanteil_35a=invoice.lohnanteil_35a,
            geraeteanteil_35a=invoice.geraeteanteil_35a,
            dankessatz=invoice.dankessatz,
            hinweise=invoice.hinweise,
            netto=invoice.netto,
            mwst_betrag=invoice.mwst_betrag,
            brutto=invoice.brutto,
            positionen=invoice.positionen,
        )
        self.invoice_repo.create(new_inv)
        self._load_table()
        show_success(self, f"Rechnung dupliziert als {new_nr}")

    def _delete(self, invoice_id: int):
        if confirm_delete(self, "diese Rechnung"):
            self.invoice_repo.delete(invoice_id)
            self._load_table()
            show_success(self, "Rechnung gelöscht.")

    def on_search(self):
        self.search_bar.search_input.setFocus()
