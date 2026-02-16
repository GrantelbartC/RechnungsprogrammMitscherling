from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QScrollArea, QCheckBox,
)
from PySide6.QtCore import Qt

from db.database import Database
from db.repos.article_repo import ArticleRepo
from models.article import Article
from ui.widgets import (
    FormCard, confirm_delete, show_success, show_error,
    create_currency_spinbox, create_mwst_combo,
)


class ArticlesTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.repo = ArticleRepo(db)
        self.current_article: Article | None = None

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Linke Seite: Liste
        left = QWidget()
        left_layout = QVBoxLayout(left)

        header_layout = QHBoxLayout()
        title = QLabel("Artikel")
        title.setProperty("cssClass", "heading")
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_new = QPushButton("+ Neu")
        btn_new.setProperty("cssClass", "primary")
        btn_new.clicked.connect(self.on_new)
        header_layout.addWidget(btn_new)
        left_layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Bezeichnung", "Netto", "MwSt", "§35a"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_table_double_click)
        left_layout.addWidget(self.table)

        # Linke Seite: Formular
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_widget = QWidget()
        form_layout = QVBoxLayout(left_widget)
        form_layout.setContentsMargins(16, 16, 16, 16)

        form_title = QLabel("Details")
        form_title.setProperty("cssClass", "subheading")
        form_layout.addWidget(form_title)

        card = FormCard("Artikeldaten")
        self.inp_bezeichnung = QLineEdit()
        self.inp_beschreibung = QTextEdit()
        self.inp_beschreibung.setMaximumHeight(80)
        self.inp_preis = create_currency_spinbox()
        self.inp_mwst = create_mwst_combo()
        self.inp_35a = QCheckBox("Begünstigt nach §35a EStG")

        card.add_field("Bezeichnung *", self.inp_bezeichnung)
        card.add_field("Beschreibung", self.inp_beschreibung)
        card.add_field("Nettopreis", self.inp_preis)
        card.add_field("MwSt-Satz", self.inp_mwst)
        card.add_row(self.inp_35a)
        form_layout.addWidget(card)

        # Brutto-Vorschau
        self.lbl_brutto = QLabel("Bruttopreis: 0,00 €")
        self.lbl_brutto.setProperty("cssClass", "subheading")
        form_layout.addWidget(self.lbl_brutto)

        self.inp_preis.valueChanged.connect(self._update_brutto_preview)
        self.inp_mwst.currentIndexChanged.connect(self._update_brutto_preview)

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
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()

        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)
        splitter.addWidget(left)
        splitter.setSizes([400, 450])

        self._load_table()

    def _load_table(self):
        articles = self.repo.get_all()
        self.table.setRowCount(len(articles))
        for row, a in enumerate(articles):
            name_item = QTableWidgetItem(a.bezeichnung)
            name_item.setData(Qt.ItemDataRole.UserRole, a.id)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(f"{a.preis:.2f} €"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{a.mwst:.0f}%"))
            badge = QTableWidgetItem("§35a" if a.beguenstigt_35a else "")
            self.table.setItem(row, 3, badge)

    def _on_table_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            article_id = item.data(Qt.ItemDataRole.UserRole)
            article = self.repo.get_by_id(article_id)
            if article:
                self._load_form(article)

    def _load_form(self, a: Article):
        self.current_article = a
        self.inp_bezeichnung.setText(a.bezeichnung)
        self.inp_beschreibung.setPlainText(a.beschreibung or "")
        self.inp_preis.setValue(a.preis)
        # Set MwSt combo
        for i in range(self.inp_mwst.count()):
            if self.inp_mwst.itemData(i) == a.mwst:
                self.inp_mwst.setCurrentIndex(i)
                break
        self.inp_35a.setChecked(a.beguenstigt_35a)
        self._update_brutto_preview()

    def _clear_form(self):
        self.current_article = None
        self.inp_bezeichnung.clear()
        self.inp_beschreibung.clear()
        self.inp_preis.setValue(0)
        self.inp_mwst.setCurrentIndex(0)
        self.inp_35a.setChecked(False)
        self._update_brutto_preview()

    def _read_form(self) -> Article:
        a = self.current_article or Article()
        a.bezeichnung = self.inp_bezeichnung.text().strip()
        a.beschreibung = self.inp_beschreibung.toPlainText().strip() or None
        a.preis = self.inp_preis.value()
        a.mwst = self.inp_mwst.currentData()
        a.beguenstigt_35a = self.inp_35a.isChecked()
        return a

    def _update_brutto_preview(self):
        preis = self.inp_preis.value()
        mwst = self.inp_mwst.currentData() or 19.0
        brutto = preis * (1 + mwst / 100)
        self.lbl_brutto.setText(f"Bruttopreis: {brutto:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))

    def on_new(self):
        self._clear_form()
        self.inp_bezeichnung.setFocus()

    def on_save(self):
        if not self.inp_bezeichnung.text().strip():
            show_error(self, "Bezeichnung ist ein Pflichtfeld.")
            return

        a = self._read_form()
        if a.id:
            self.repo.update(a)
            show_success(self, "Artikel aktualisiert.")
        else:
            a.id = self.repo.create(a)
            self.current_article = a
            show_success(self, "Artikel angelegt.")
        self._load_table()

    def _on_delete(self):
        if not self.current_article or not self.current_article.id:
            return
        if confirm_delete(self, f'"{self.current_article.bezeichnung}"'):
            self.repo.delete(self.current_article.id)
            self._clear_form()
            self._load_table()
            show_success(self, "Artikel gelöscht.")
