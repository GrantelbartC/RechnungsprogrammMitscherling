from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QWidget, QVBoxLayout, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from db.database import Database
from ui.theme import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setWindowTitle("Rechnungsprogramm")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._create_tabs()

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage(f"Datenbank: {db.db_path}")

        self._setup_shortcuts()

    def _create_tabs(self):
        from ui.suppliers import SuppliersTab
        from ui.customers import CustomersTab
        from ui.articles import ArticlesTab
        from ui.invoices import InvoicesTab
        from ui.kostenvoranschlaege import KostenvoranschlaegeTab
        from ui.firmenschreiben import FirmenschreibenTab
        from ui.text_assistant import TextAssistantTab
        from ui.archive import ArchiveTab
        from ui.mahnwesen import MahnwesenTab
        from ui.banking import BankingTab
        from ui.settings import SettingsTab

        self.suppliers_tab = SuppliersTab(self.db)
        self.customers_tab = CustomersTab(self.db)
        self.articles_tab = ArticlesTab(self.db)
        self.invoices_tab = InvoicesTab(self.db)
        self.kv_tab = KostenvoranschlaegeTab(self.db)
        self.fs_tab = FirmenschreibenTab(self.db)
        self.text_assistant_tab = TextAssistantTab(self.db)
        self.archive_tab = ArchiveTab(self.db)
        self.mahnwesen_tab = MahnwesenTab(self.db)
        self.banking_tab = BankingTab(self.db)
        self.settings_tab = SettingsTab(self.db)

        self.tabs.addTab(self.suppliers_tab, "Rechnungssteller")
        self.tabs.addTab(self.customers_tab, "Kunden")
        self.tabs.addTab(self.articles_tab, "Artikel")
        self.tabs.addTab(self.invoices_tab, "Rechnung erstellen")
        self.tabs.addTab(self.kv_tab, "Kostenvoranschlag")
        self.tabs.addTab(self.fs_tab, "Firmenschreiben")
        self.tabs.addTab(self.text_assistant_tab, "Textassistent")
        self.tabs.addTab(self.archive_tab, "Archiv")
        self.tabs.addTab(self.mahnwesen_tab, "Mahnwesen")
        self.tabs.addTab(self.banking_tab, "Bank")
        self.tabs.addTab(self.settings_tab, "Einstellungen")

    def _setup_shortcuts(self):
        for i in range(min(self.tabs.count(), 9)):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            shortcut.activated.connect(lambda idx=i: self.tabs.setCurrentIndex(idx))

        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._on_new)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._on_save)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._on_search)

    def _on_new(self):
        current = self.tabs.currentWidget()
        if hasattr(current, "on_new"):
            current.on_new()

    def _on_save(self):
        current = self.tabs.currentWidget()
        if hasattr(current, "on_save"):
            current.on_save()

    def _on_search(self):
        current = self.tabs.currentWidget()
        if hasattr(current, "on_search"):
            current.on_search()

    def set_status(self, message: str):
        self.statusbar.showMessage(message, 5000)
