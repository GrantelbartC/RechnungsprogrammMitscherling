from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from db.database import Database
from db.repos.invoice_repo import InvoiceRepo
from db.repos.supplier_repo import SupplierRepo
from models.banking import BankConnection, BankOperationResult, PendingTanSession
from services.banking import BankingService, BankingServiceError
from ui.widgets import FormCard, show_error, show_success
from utils.bank_settings import get_bank_product_id, set_bank_product_id


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class BankWorker(QRunnable):
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class TanDialog(QDialog):
    def __init__(self, session: PendingTanSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("TAN bestaetigen")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        if session.challenge_html:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(False)
            browser.setHtml(session.challenge_html)
            browser.setMaximumHeight(140)
            layout.addWidget(browser)
        elif session.challenge_text:
            label = QLabel(session.challenge_text)
            label.setWordWrap(True)
            layout.addWidget(label)

        if session.challenge_matrix_data:
            image_label = QLabel()
            pixmap = QPixmap()
            pixmap.loadFromData(session.challenge_matrix_data)
            image_label.setPixmap(pixmap.scaledToWidth(260, Qt.TransformationMode.SmoothTransformation))
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(image_label)

        if session.decoupled:
            info = QLabel("Bitte bestaetigen Sie den Vorgang in Ihrer Banking-App und klicken Sie danach auf Weiter.")
            info.setWordWrap(True)
            layout.addWidget(info)
            self.tan_input = None
        else:
            form = QFormLayout()
            self.tan_input = QLineEdit()
            self.tan_input.setPlaceholderText("TAN")
            form.addRow("TAN", self.tan_input)
            layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        if session.decoupled:
            ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
            ok_button.setText("Weiter")
        layout.addWidget(buttons)

    def tan_value(self) -> str:
        if not self.tan_input:
            return ""
        return self.tan_input.text().strip()


class BankingTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.service = BankingService(db)
        self.supplier_repo = SupplierRepo(db)
        self.invoice_repo = InvoiceRepo(db)
        self.thread_pool = QThreadPool(self)
        self._workers: set[BankWorker] = set()
        self._active_pin: str | None = None
        self._pending_tan_session: PendingTanSession | None = None
        self._continue_sync_after_balance = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        title = QLabel("Bank")
        title.setProperty("cssClass", "heading")
        self.main_layout.addWidget(title)

        self._build_supplier_card()
        self._build_connection_card()
        self._build_accounts_card()
        self._build_transactions_card()
        self._build_suggestions_card()

        self.main_layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_supplier_card(self):
        card = FormCard("Rechnungssteller")
        self.cmb_supplier = QComboBox()
        self.cmb_supplier.currentIndexChanged.connect(self._on_supplier_changed)
        card.add_field("Rechnungssteller", self.cmb_supplier)

        self.lbl_connection_info = QLabel("Noch keine Bankverbindung gespeichert.")
        self.lbl_connection_info.setProperty("cssClass", "secondary")
        self.lbl_connection_info.setWordWrap(True)
        card.add_row(self.lbl_connection_info)
        self.main_layout.addWidget(card)

    def _build_connection_card(self):
        card = FormCard("FinTS-Zugang")
        self.inp_product_id = QLineEdit()
        self.inp_product_id.setPlaceholderText("DK product_id")
        self.inp_blz = QLineEdit()
        self.inp_blz.setPlaceholderText("BLZ")
        self.inp_url = QLineEdit()
        self.inp_url.setPlaceholderText("https://...")
        self.inp_user_id = QLineEdit()
        self.inp_customer_id = QLineEdit()
        self.inp_tan_medium = QLineEdit()

        card.add_field("product_id *", self.inp_product_id)
        card.add_field("BLZ *", self.inp_blz)
        card.add_field("FinTS-URL *", self.inp_url)
        card.add_field("Benutzerkennung *", self.inp_user_id)
        card.add_field("Kunden-ID", self.inp_customer_id)
        card.add_field("TAN-Medium", self.inp_tan_medium)

        button_row = QHBoxLayout()
        self.btn_save_connection = QPushButton("Verbindung speichern")
        self.btn_save_connection.setProperty("cssClass", "primary")
        self.btn_save_connection.clicked.connect(self._on_save_connection)
        self.btn_load_accounts = QPushButton("Konten abrufen")
        self.btn_load_accounts.clicked.connect(self._on_load_accounts)
        button_row.addWidget(self.btn_save_connection)
        button_row.addWidget(self.btn_load_accounts)
        button_row.addStretch()
        button_widget = QWidget()
        button_widget.setLayout(button_row)
        card.add_row(button_widget)

        self.main_layout.addWidget(card)

    def _build_accounts_card(self):
        card = FormCard("Konten")
        header = QHBoxLayout()
        self.lbl_last_sync = QLabel("Letzter Sync: -")
        self.lbl_last_sync.setProperty("cssClass", "secondary")
        self.lbl_balance = QLabel("Kontostand: -")
        self.lbl_balance.setProperty("cssClass", "subheading")
        header.addWidget(self.lbl_last_sync)
        header.addStretch()
        header.addWidget(self.lbl_balance)
        header_widget = QWidget()
        header_widget.setLayout(header)
        card.add_row(header_widget)

        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(6)
        self.accounts_table.setHorizontalHeaderLabels(
            ["Konto", "IBAN", "Waehrung", "Kontostand", "Stand", "Standard"]
        )
        self.accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.accounts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.accounts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.accounts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.accounts_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.accounts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.accounts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.accounts_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        card.add_row(self.accounts_table)

        actions = QHBoxLayout()
        self.btn_set_default = QPushButton("Als Standard setzen")
        self.btn_set_default.clicked.connect(self._on_set_default_account)
        self.btn_sync = QPushButton("Synchronisieren")
        self.btn_sync.setProperty("cssClass", "primary")
        self.btn_sync.clicked.connect(self._on_sync)
        actions.addWidget(self.btn_set_default)
        actions.addStretch()
        actions.addWidget(self.btn_sync)
        actions_widget = QWidget()
        actions_widget.setLayout(actions)
        card.add_row(actions_widget)

        self.main_layout.addWidget(card)

    def _build_transactions_card(self):
        card = FormCard("Umsaetze")
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(7)
        self.transactions_table.setHorizontalHeaderLabels(
            ["Buchung", "Valuta", "Betrag", "Gegenpartei", "Verwendungszweck", "Status", "Match"]
        )
        self.transactions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.transactions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.transactions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.transactions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        card.add_row(self.transactions_table)
        self.main_layout.addWidget(card)

    def _build_suggestions_card(self):
        card = FormCard("Zahlungsvorschlaege")
        self.suggestions_table = QTableWidget()
        self.suggestions_table.setColumnCount(6)
        self.suggestions_table.setHorizontalHeaderLabels(
            ["Buchung", "Betrag", "Rechnung", "Score", "Grund", "Aktionen"]
        )
        self.suggestions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.suggestions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.suggestions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        card.add_row(self.suggestions_table)
        self.main_layout.addWidget(card)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_suppliers()

    def _refresh_suppliers(self):
        current_supplier = self.cmb_supplier.currentData()
        self.cmb_supplier.blockSignals(True)
        self.cmb_supplier.clear()
        self.cmb_supplier.addItem("-- Bitte waehlen --", None)
        for supplier in self.supplier_repo.get_all():
            self.cmb_supplier.addItem(supplier.firma, supplier.id)
        if current_supplier:
            index = self.cmb_supplier.findData(current_supplier)
            if index >= 0:
                self.cmb_supplier.setCurrentIndex(index)
        self.cmb_supplier.blockSignals(False)
        self.inp_product_id.setText(get_bank_product_id())
        if self.cmb_supplier.currentData():
            self._load_supplier_data(self.cmb_supplier.currentData())
        else:
            self._clear_supplier_view()

    def _on_supplier_changed(self, _index):
        supplier_id = self.cmb_supplier.currentData()
        if supplier_id:
            self._load_supplier_data(supplier_id)
        else:
            self._clear_supplier_view()

    def _load_supplier_data(self, supplier_id: int):
        connection = self.service.get_connection_for_supplier(supplier_id)
        self.inp_product_id.setText(get_bank_product_id())
        if not connection:
            self.lbl_connection_info.setText("Noch keine Bankverbindung gespeichert.")
            self.inp_blz.clear()
            self.inp_url.clear()
            self.inp_user_id.clear()
            self.inp_customer_id.clear()
            self.inp_tan_medium.clear()
            self._populate_accounts([])
            self._populate_transactions([])
            self._populate_suggestions([])
            self.lbl_last_sync.setText("Letzter Sync: -")
            self.lbl_balance.setText("Kontostand: -")
            return

        self.inp_blz.setText(connection.bank_code_blz or "")
        self.inp_url.setText(connection.fints_url or "")
        self.inp_user_id.setText(connection.user_id or "")
        self.inp_customer_id.setText(connection.customer_id or "")
        self.inp_tan_medium.setText(connection.tan_medium or "")
        self.lbl_connection_info.setText(
            f"Bankzugang fuer Rechnungssteller #{connection.supplier_id} gespeichert."
        )
        self._refresh_connection_views(connection.id)

    def _clear_supplier_view(self):
        self.lbl_connection_info.setText("Bitte zuerst einen Rechnungssteller auswaehlen.")
        self.inp_product_id.setText(get_bank_product_id())
        self.inp_blz.clear()
        self.inp_url.clear()
        self.inp_user_id.clear()
        self.inp_customer_id.clear()
        self.inp_tan_medium.clear()
        self._populate_accounts([])
        self._populate_transactions([])
        self._populate_suggestions([])
        self.lbl_last_sync.setText("Letzter Sync: -")
        self.lbl_balance.setText("Kontostand: -")

    def _refresh_connection_views(self, connection_id: int):
        accounts = self.service.get_accounts_for_connection(connection_id)
        self._populate_accounts(accounts)
        default_account = self.service.get_default_account(connection_id)
        if default_account:
            self.lbl_balance.setText(f"Kontostand: {self._format_currency(default_account.current_balance)}")
        else:
            self.lbl_balance.setText("Kontostand: -")

        connection = self.service.connection_repo.get_by_id(connection_id)
        if connection and connection.last_sync_at:
            self.lbl_last_sync.setText(f"Letzter Sync: {self._format_datetime(connection.last_sync_at)}")
        else:
            self.lbl_last_sync.setText("Letzter Sync: -")

        if default_account:
            self._populate_transactions(self.service.get_transactions_for_account(default_account.id))
            self._populate_suggestions(self.service.get_suggestions_for_account(default_account.id))
        else:
            self._populate_transactions([])
            self._populate_suggestions([])

    def _populate_accounts(self, accounts):
        self.accounts_table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            display = QTableWidgetItem(account.display_name or "Bankkonto")
            display.setData(Qt.ItemDataRole.UserRole, account.id)
            self.accounts_table.setItem(row, 0, display)
            self.accounts_table.setItem(row, 1, QTableWidgetItem(account.iban or ""))
            self.accounts_table.setItem(row, 2, QTableWidgetItem(account.currency or ""))
            self.accounts_table.setItem(row, 3, QTableWidgetItem(self._format_currency(account.current_balance)))
            self.accounts_table.setItem(row, 4, QTableWidgetItem(self._format_date(account.balance_date)))
            self.accounts_table.setItem(row, 5, QTableWidgetItem("Ja" if account.is_default else ""))

    def _populate_transactions(self, rows):
        self.transactions_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            transaction = entry["transaction"]
            self.transactions_table.setItem(row, 0, QTableWidgetItem(self._format_date(transaction.booking_date)))
            self.transactions_table.setItem(row, 1, QTableWidgetItem(self._format_date(transaction.value_date)))
            self.transactions_table.setItem(row, 2, QTableWidgetItem(self._format_currency(transaction.amount)))
            self.transactions_table.setItem(row, 3, QTableWidgetItem(transaction.counterparty_name or ""))
            self.transactions_table.setItem(row, 4, QTableWidgetItem(transaction.purpose or ""))
            status_label = "Gebucht" if transaction.status == "booked" else "Pending"
            self.transactions_table.setItem(row, 5, QTableWidgetItem(status_label))
            self.transactions_table.setItem(row, 6, QTableWidgetItem(entry["match_label"]))

    def _populate_suggestions(self, rows):
        self.suggestions_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            self.suggestions_table.setItem(row, 0, QTableWidgetItem(self._format_date(entry.get("booking_date"))))
            self.suggestions_table.setItem(row, 1, QTableWidgetItem(self._format_currency(entry.get("amount"))))
            invoice_item = QTableWidgetItem(entry.get("rechnungsnr") or "")
            invoice_item.setData(Qt.ItemDataRole.UserRole, entry.get("invoice_id"))
            self.suggestions_table.setItem(row, 2, invoice_item)
            self.suggestions_table.setItem(row, 3, QTableWidgetItem(str(entry.get("score") or 0)))
            self.suggestions_table.setItem(row, 4, QTableWidgetItem(entry.get("reason_text") or ""))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            btn_confirm = QPushButton("Bestaetigen")
            btn_confirm.clicked.connect(
                lambda _, tx_id=entry["bank_transaction_id"], invoice_id=entry["invoice_id"]: self._on_confirm_match(tx_id, invoice_id)
            )
            btn_reject = QPushButton("Ablehnen")
            btn_reject.clicked.connect(
                lambda _, tx_id=entry["bank_transaction_id"], invoice_id=entry["invoice_id"]: self._on_reject_match(tx_id, invoice_id)
            )
            btn_open = QPushButton("Rechnung")
            btn_open.clicked.connect(lambda _, invoice_id=entry["invoice_id"]: self._open_invoice(invoice_id))
            actions_layout.addWidget(btn_confirm)
            actions_layout.addWidget(btn_reject)
            actions_layout.addWidget(btn_open)
            self.suggestions_table.setCellWidget(row, 5, actions_widget)

    def _on_save_connection(self):
        try:
            connection = self._save_connection_data()
        except BankingServiceError as exc:
            show_error(self, str(exc))
            return
        self.lbl_connection_info.setText(f"Bankzugang fuer Rechnungssteller #{connection.supplier_id} gespeichert.")
        show_success(self, "Bankverbindung gespeichert.")
        self._refresh_connection_views(connection.id)

    def _on_load_accounts(self):
        try:
            connection = self._save_connection_data()
        except BankingServiceError as exc:
            show_error(self, str(exc))
            return
        pin = self._prompt_pin()
        if pin is None:
            return
        self._active_pin = pin
        self._continue_sync_after_balance = False
        self._run_worker(
            self.service.fetch_accounts,
            connection.id,
            pin,
            get_bank_product_id(),
            on_result=self._handle_operation_result,
        )

    def _on_set_default_account(self):
        connection = self._current_connection()
        selected_account_id = self._selected_account_id()
        if not connection or not selected_account_id:
            show_error(self, "Bitte zuerst ein Konto auswaehlen.")
            return
        try:
            self.service.set_default_account(connection.id, selected_account_id)
        except BankingServiceError as exc:
            show_error(self, str(exc))
            return
        self._refresh_connection_views(connection.id)
        self.window().set_status("Standardkonto aktualisiert.")

    def _on_sync(self):
        connection = self._current_connection()
        if not connection:
            show_error(self, "Bitte zuerst eine Bankverbindung speichern.")
            return
        default_account = self.service.get_default_account(connection.id)
        if not default_account:
            show_error(self, "Bitte zuerst ein Standardkonto festlegen.")
            return
        pin = self._prompt_pin()
        if pin is None:
            return
        self._active_pin = pin
        self._continue_sync_after_balance = True
        self._run_worker(
            self.service.fetch_balance,
            connection.id,
            default_account.id,
            pin,
            get_bank_product_id(),
            on_result=self._handle_operation_result,
        )

    def _handle_operation_result(self, result: BankOperationResult):
        if result.pending_tan_session:
            self._pending_tan_session = result.pending_tan_session
            dialog = TanDialog(result.pending_tan_session, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                self._clear_flow_state()
                return
            tan = dialog.tan_value()
            self._run_worker(
                self.service.resume_pending_tan,
                result.pending_tan_session,
                self._active_pin or "",
                get_bank_product_id(),
                tan,
                on_result=self._handle_operation_result,
            )
            return

        self._pending_tan_session = None
        if result.action == BankingService.ACTION_LOAD_ACCOUNTS:
            self._refresh_connection_views(result.connection_id)
            show_success(self, "Konten erfolgreich geladen.")
            self._clear_flow_state()
            return

        if result.action == BankingService.ACTION_FETCH_BALANCE:
            self._refresh_connection_views(result.connection_id)
            if self._continue_sync_after_balance:
                default_account = self.service.get_default_account(result.connection_id)
                if default_account:
                    self._run_worker(
                        self.service.fetch_transactions,
                        result.connection_id,
                        default_account.id,
                        self._active_pin or "",
                        get_bank_product_id(),
                        None,
                        None,
                        on_result=self._handle_operation_result,
                    )
                    return
            self._clear_flow_state()
            return

        if result.action == BankingService.ACTION_FETCH_TRANSACTIONS:
            self._refresh_connection_views(result.connection_id)
            summary = result.sync_result
            if summary:
                show_success(
                    self,
                    f"Synchronisation abgeschlossen: {summary.imported_count} neue, {summary.updated_count} aktualisierte Umsaetze, {summary.suggested_count} Vorschlaege.",
                )
            self._clear_flow_state()

    def _on_confirm_match(self, transaction_id: int, invoice_id: int):
        try:
            self.service.confirm_match(transaction_id, invoice_id)
        except BankingServiceError as exc:
            show_error(self, str(exc))
            return
        self._reload_current_connection()
        archive_tab = getattr(self.window(), "archive_tab", None)
        if archive_tab and hasattr(archive_tab, "_load_table"):
            archive_tab._load_table()
        show_success(self, "Zahlung bestaetigt und Rechnung als bezahlt markiert.")

    def _on_reject_match(self, transaction_id: int, invoice_id: int):
        try:
            self.service.reject_match(transaction_id, invoice_id)
        except BankingServiceError as exc:
            show_error(self, str(exc))
            return
        self._reload_current_connection()
        show_success(self, "Vorschlag abgelehnt.")

    def _run_worker(self, func: Callable, *args, on_result: Callable):
        worker = BankWorker(func, *args)
        self._workers.add(worker)
        self._set_busy(True)
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(lambda worker=worker: self._on_worker_finished(worker))
        self.thread_pool.start(worker)

    def _on_worker_error(self, message: str):
        self._clear_flow_state()
        show_error(self, message)

    def _on_worker_finished(self, worker: BankWorker):
        self._workers.discard(worker)
        if not self._workers:
            self._set_busy(False)

    def _set_busy(self, busy: bool):
        self.cmb_supplier.setEnabled(not busy)
        self.btn_save_connection.setEnabled(not busy)
        self.btn_load_accounts.setEnabled(not busy)
        self.btn_set_default.setEnabled(not busy)
        self.btn_sync.setEnabled(not busy)
        if hasattr(self.window(), "set_status"):
            self.window().set_status("Bankvorgang laeuft..." if busy else "Bereit")

    def _save_connection_data(self) -> BankConnection:
        supplier_id = self.cmb_supplier.currentData()
        if not supplier_id:
            raise BankingServiceError("Bitte zuerst einen Rechnungssteller auswaehlen.")

        product_id = self.inp_product_id.text().strip()
        if not product_id:
            raise BankingServiceError("Die app-weite product_id ist erforderlich.")
        set_bank_product_id(product_id)

        existing = self.service.get_connection_for_supplier(supplier_id)
        connection = existing or BankConnection(supplier_id=supplier_id)
        connection.bank_code_blz = self.inp_blz.text().strip()
        connection.fints_url = self.inp_url.text().strip()
        connection.user_id = self.inp_user_id.text().strip()
        connection.customer_id = self.inp_customer_id.text().strip() or None
        connection.tan_medium = self.inp_tan_medium.text().strip() or None
        return self.service.save_connection(connection)

    def _prompt_pin(self) -> str | None:
        pin, ok = QInputDialog.getText(
            self,
            "PIN eingeben",
            "PIN:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return None
        pin = pin.strip()
        if not pin:
            show_error(self, "PIN darf nicht leer sein.")
            return None
        return pin

    def _current_connection(self) -> BankConnection | None:
        supplier_id = self.cmb_supplier.currentData()
        if not supplier_id:
            return None
        return self.service.get_connection_for_supplier(supplier_id)

    def _selected_account_id(self) -> int | None:
        row = self.accounts_table.currentRow()
        if row < 0:
            return None
        item = self.accounts_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _reload_current_connection(self):
        connection = self._current_connection()
        if connection:
            self._refresh_connection_views(connection.id)

    def _open_invoice(self, invoice_id: int):
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            show_error(self, "Rechnung konnte nicht geladen werden.")
            return
        main_window = self.window()
        if hasattr(main_window, "tabs") and hasattr(main_window, "invoices_tab"):
            main_window.invoices_tab.load_invoice(invoice)
            main_window.tabs.setCurrentWidget(main_window.invoices_tab)

    def _clear_flow_state(self):
        self._active_pin = None
        self._pending_tan_session = None
        self._continue_sync_after_balance = False

    def _format_currency(self, value) -> str:
        if value is None:
            return "-"
        return f"{float(value):,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")

    def _format_date(self, value) -> str:
        if not value:
            return ""
        if isinstance(value, str):
            parts = value.split("-")
            if len(parts) == 3:
                return f"{parts[2]}.{parts[1]}.{parts[0]}"
            return value
        return value.strftime("%d.%m.%Y")

    def _format_datetime(self, value) -> str:
        if not value:
            return "-"
        if isinstance(value, str):
            try:
                value = value.replace("T", " ")
                return value[:16]
            except Exception:
                return value
        return value.strftime("%d.%m.%Y %H:%M")
