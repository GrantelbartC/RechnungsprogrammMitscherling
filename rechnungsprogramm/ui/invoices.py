from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QCheckBox, QDoubleSpinBox, QSpinBox, QScrollArea,
    QGroupBox, QFormLayout, QDateEdit, QRadioButton, QButtonGroup,
    QFileDialog, QAbstractSpinBox,
)
from PySide6.QtCore import Qt, QDate
from datetime import date

from db.database import Database
from db.repos.supplier_repo import SupplierRepo
from db.repos.customer_repo import CustomerRepo
from db.repos.article_repo import ArticleRepo
from db.repos.invoice_repo import InvoiceRepo
from db.repos.number_repo import NumberRepo
from models.invoice import Invoice, InvoiceLine
from models.supplier import Supplier
from models.customer import Customer
from ui.widgets import (
    FormCard, show_success, show_error,
    create_date_edit, create_currency_spinbox, create_mwst_combo,
    NoScrollDoubleSpinBox, NoScrollSpinBox,
)
from utils.calculations import berechne_rechnung, berechne_position


class InvoicesTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.supplier_repo = SupplierRepo(db)
        self.customer_repo = CustomerRepo(db)
        self.article_repo = ArticleRepo(db)
        self.invoice_repo = InvoiceRepo(db)
        self.number_repo = NumberRepo(db)
        self.current_invoice: Invoice | None = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        title = QLabel("Rechnung erstellen")
        title.setProperty("cssClass", "heading")
        self.main_layout.addWidget(title)

        self._build_kopfdaten()
        self._build_positionen()
        self._build_rabatt()
        self._build_zusatzdaten()
        self._build_summen()
        self._build_buttons()

        self.main_layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_kopfdaten(self):
        card = FormCard("Kopfdaten")

        # Rechnungssteller
        self.cmb_supplier = QComboBox()
        self.cmb_supplier.currentIndexChanged.connect(self._on_supplier_changed)
        card.add_field("Rechnungssteller *", self.cmb_supplier)

        self.lbl_supplier_info = QLabel("")
        self.lbl_supplier_info.setProperty("cssClass", "secondary")
        self.lbl_supplier_info.setWordWrap(True)
        card.add_row(self.lbl_supplier_info)

        # Kunde
        self.cmb_customer = QComboBox()
        self.cmb_customer.currentIndexChanged.connect(self._on_customer_changed)
        card.add_field("Kunde *", self.cmb_customer)

        self.lbl_customer_info = QLabel("")
        self.lbl_customer_info.setProperty("cssClass", "secondary")
        self.lbl_customer_info.setWordWrap(True)
        card.add_row(self.lbl_customer_info)

        # Rechnungsnummer
        nr_layout = QHBoxLayout()
        self.inp_rechnungsnr = QLineEdit()
        self.inp_rechnungsnr.setPlaceholderText("Automatisch")
        self.btn_auto_nr = QPushButton("Auto")
        self.btn_auto_nr.clicked.connect(self._generate_number)
        nr_layout.addWidget(self.inp_rechnungsnr)
        nr_layout.addWidget(self.btn_auto_nr)
        nr_widget = QWidget()
        nr_widget.setLayout(nr_layout)
        card.add_field("Rechnungsnr.", nr_widget)

        # Datum
        self.inp_datum = create_date_edit()
        self.inp_datum.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        card.add_field("Rechnungsdatum *", self.inp_datum)

        # Zahlungsziel
        self.inp_zahlungsziel = NoScrollSpinBox()
        self.inp_zahlungsziel.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.inp_zahlungsziel.setRange(0, 365)
        self.inp_zahlungsziel.setValue(14)
        self.inp_zahlungsziel.setSuffix(" Tage")
        card.add_field("Zahlungsziel", self.inp_zahlungsziel)

        # Betreff
        self.inp_betreff = QLineEdit()
        card.add_field("Betreff", self.inp_betreff)

        # Objekt/WEG
        self.inp_objekt = QLineEdit()
        card.add_field("Objekt / WEG", self.inp_objekt)

        # Ausführungsdatum
        self.inp_ausfuehrung = create_date_edit(default_today=False)
        self.inp_ausfuehrung.setSpecialValueText(" ")
        self.inp_ausfuehrung.setDate(self.inp_ausfuehrung.minimumDate())
        self.inp_ausfuehrung.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        card.add_field("Tag der Ausführung", self.inp_ausfuehrung)

        # Zeitraum
        self.inp_zeitraum = QLineEdit()
        self.inp_zeitraum.setPlaceholderText("z.B. 01.01.2026 - 31.01.2026")
        card.add_field("Ausführungszeitraum", self.inp_zeitraum)

        self.main_layout.addWidget(card)

    def _build_positionen(self):
        card = FormCard("Positionen")

        self.pos_table = QTableWidget()
        self.pos_table.setColumnCount(8)
        self.pos_table.setHorizontalHeaderLabels([
            "Artikel", "Beschreibung", "Menge", "Einzelpreis", "MwSt", "§35a", "Gesamt", ""
        ])
        header = self.pos_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.pos_table.setColumnWidth(0, 180)
        self.pos_table.setColumnWidth(2, 80)
        self.pos_table.setColumnWidth(3, 110)
        self.pos_table.setColumnWidth(4, 90)
        self.pos_table.setColumnWidth(6, 100)
        self.pos_table.setColumnWidth(7, 40)
        self.pos_table.verticalHeader().setDefaultSectionSize(50)
        self.pos_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card.add_row(self.pos_table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ Position hinzufügen")
        btn_add.setProperty("cssClass", "primary")
        btn_add.clicked.connect(self._add_position_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        card.add_row(btn_widget)

        self.main_layout.addWidget(card)
        self._update_position_table_height()

    def _update_position_table_height(self):
        """Passt die Tabellenhöhe so an, dass alle Positionszeilen sichtbar sind."""
        header_height = self.pos_table.horizontalHeader().height()
        rows_height = sum(self.pos_table.rowHeight(row) for row in range(self.pos_table.rowCount()))
        frame_height = self.pos_table.frameWidth() * 2
        scrollbar_height = (
            self.pos_table.horizontalScrollBar().height()
            if self.pos_table.horizontalScrollBar().isVisible()
            else 0
        )
        content_height = header_height + rows_height + frame_height + scrollbar_height + 4
        self.pos_table.setFixedHeight(max(200, content_height))

    def _build_rabatt(self):
        card = FormCard("Rabatt (optional)")

        self.chk_rabatt = QCheckBox("Rabatt aktivieren")
        self.chk_rabatt.toggled.connect(self._toggle_rabatt)
        card.add_row(self.chk_rabatt)

        self.rabatt_widget = QWidget()
        rabatt_layout = QHBoxLayout(self.rabatt_widget)
        self.rb_prozent = QRadioButton("Prozent (%)")
        self.rb_betrag = QRadioButton("Betrag (€)")
        self.rb_prozent.setChecked(True)
        self.rabatt_group = QButtonGroup()
        self.rabatt_group.addButton(self.rb_prozent)
        self.rabatt_group.addButton(self.rb_betrag)
        self.inp_rabatt_wert = NoScrollDoubleSpinBox()
        self.inp_rabatt_wert.setRange(0, 999999)
        self.inp_rabatt_wert.setDecimals(2)
        self.inp_rabatt_wert.valueChanged.connect(self._update_summen)
        rabatt_layout.addWidget(self.rb_prozent)
        rabatt_layout.addWidget(self.rb_betrag)
        rabatt_layout.addWidget(self.inp_rabatt_wert)
        self.rabatt_widget.setVisible(False)
        card.add_row(self.rabatt_widget)

        self.main_layout.addWidget(card)

    def _build_zusatzdaten(self):
        card = FormCard("Zusatzdaten")

        self.lbl_35a = QLabel("0,00 €")
        self.lbl_35a.setStyleSheet("font-weight: bold; padding: 4px;")
        card.add_field("Lohn- & Geräteanteil §35a", self.lbl_35a)

        self.inp_dankessatz = QTextEdit()
        self.inp_dankessatz.setMaximumHeight(60)
        card.add_field("Dankessatz", self.inp_dankessatz)

        self.inp_hinweise = QTextEdit()
        self.inp_hinweise.setMaximumHeight(60)
        card.add_field("Weitere Hinweise", self.inp_hinweise)

        self.main_layout.addWidget(card)

    def _build_summen(self):
        card = FormCard("Summen")
        self.lbl_netto = QLabel("Netto: 0,00 €")
        self.lbl_rabatt = QLabel("")
        self.lbl_netto_nach_rabatt = QLabel("")
        self.lbl_mwst = QLabel("MwSt: 0,00 €")
        self.lbl_brutto = QLabel("Brutto: 0,00 €")
        self.lbl_brutto.setProperty("cssClass", "heading")

        card.add_row(self.lbl_netto)
        card.add_row(self.lbl_rabatt)
        card.add_row(self.lbl_netto_nach_rabatt)
        card.add_row(self.lbl_mwst)
        card.add_row(self.lbl_brutto)

        self.main_layout.addWidget(card)

    def _build_buttons(self):
        # Export-Zielordner
        from utils.paths import get_rechnungen_base_dir
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Export-Zielordner:"))
        self.lbl_export_path = QLabel(str(get_rechnungen_base_dir()))
        self.lbl_export_path.setProperty("cssClass", "secondary")
        self.lbl_export_path.setWordWrap(True)
        folder_layout.addWidget(self.lbl_export_path, 1)
        btn_folder = QPushButton("Ändern...")
        btn_folder.clicked.connect(self._select_export_folder)
        folder_layout.addWidget(btn_folder)
        self.main_layout.addLayout(folder_layout)

        # ZUGFeRD-Option
        self.chk_zugferd = QCheckBox("ZUGFeRD / Factur-X einbetten (E-Rechnung)")
        self.main_layout.addWidget(self.chk_zugferd)

        btn_layout = QHBoxLayout()

        btn_clear = QPushButton("Neue Rechnung")
        btn_clear.clicked.connect(self._clear_form)

        btn_save = QPushButton("Rechnung speichern")
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
        from utils.paths import get_rechnungen_base_dir, set_rechnungen_base_dir
        current = str(get_rechnungen_base_dir())
        folder = QFileDialog.getExistingDirectory(self, "Export-Zielordner wählen", current)
        if folder:
            set_rechnungen_base_dir(folder)
            self.lbl_export_path.setText(folder)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_dropdowns()

    def _refresh_dropdowns(self):
        # Suppliers
        current_supplier = self.cmb_supplier.currentData()
        self.cmb_supplier.blockSignals(True)
        self.cmb_supplier.clear()
        self.cmb_supplier.addItem("-- Bitte wählen --", None)
        for s in self.supplier_repo.get_all():
            self.cmb_supplier.addItem(s.firma, s.id)
        if current_supplier:
            idx = self.cmb_supplier.findData(current_supplier)
            if idx >= 0:
                self.cmb_supplier.setCurrentIndex(idx)
        self.cmb_supplier.blockSignals(False)

        # Customers
        current_customer = self.cmb_customer.currentData()
        self.cmb_customer.blockSignals(True)
        self.cmb_customer.clear()
        self.cmb_customer.addItem("-- Bitte wählen --", None)
        for c in self.customer_repo.get_all():
            self.cmb_customer.addItem(c.full_name, c.id)
        if current_customer:
            idx = self.cmb_customer.findData(current_customer)
            if idx >= 0:
                self.cmb_customer.setCurrentIndex(idx)
        self.cmb_customer.blockSignals(False)

        # Refresh articles in position rows
        self._refresh_article_combos()

    def _refresh_article_combos(self):
        articles = self.article_repo.get_all()
        for row in range(self.pos_table.rowCount()):
            combo = self.pos_table.cellWidget(row, 0)
            if isinstance(combo, QComboBox):
                current_data = combo.currentData()
                current_text = combo.currentText()
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("", None)
                for a in articles:
                    combo.addItem(a.bezeichnung, a.id)
                if current_data:
                    idx = combo.findData(current_data)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                elif current_text:
                    combo.setEditText(current_text)
                combo.blockSignals(False)

    def _on_supplier_changed(self, index):
        supplier_id = self.cmb_supplier.currentData()
        if supplier_id:
            s = self.supplier_repo.get_by_id(supplier_id)
            if s:
                info_parts = [p for p in [s.strasse, f"{s.plz} {s.ort}".strip(), s.telefon, s.email] if p]
                self.lbl_supplier_info.setText(" | ".join(info_parts))
                if not self.inp_dankessatz.toPlainText().strip():
                    self.inp_dankessatz.setPlainText(s.dankessatz or "")
                return
        self.lbl_supplier_info.setText("")

    def _on_customer_changed(self, index):
        customer_id = self.cmb_customer.currentData()
        if customer_id:
            c = self.customer_repo.get_by_id(customer_id)
            if c:
                info_parts = [p for p in [c.strasse, f"{c.plz} {c.ort}".strip(), c.telefon] if p]
                self.lbl_customer_info.setText(" | ".join(info_parts))
                return
        self.lbl_customer_info.setText("")

    def _generate_number(self):
        jahr = date.today().year
        nr = self.number_repo.naechste_nummer(jahr)
        self.inp_rechnungsnr.setText(nr)

    def _add_position_row(self):
        row = self.pos_table.rowCount()
        self.pos_table.insertRow(row)

        # Artikel-Combo (editierbar - User kann frei tippen oder aus Dropdown wählen)
        cmb = QComboBox()
        cmb.setEditable(True)
        cmb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        cmb.addItem("", None)
        for a in self.article_repo.get_all():
            cmb.addItem(a.bezeichnung, a.id)
        cmb.currentIndexChanged.connect(lambda _, r=row: self._on_article_selected(r))
        self.pos_table.setCellWidget(row, 0, cmb)

        # Beschreibung
        self.pos_table.setItem(row, 1, QTableWidgetItem(""))

        # Menge
        menge = NoScrollDoubleSpinBox()
        menge.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        menge.setRange(0.01, 99999)
        menge.setValue(1.0)
        menge.setDecimals(2)
        menge.valueChanged.connect(self._update_summen)
        self.pos_table.setCellWidget(row, 2, menge)

        # Einzelpreis
        preis = NoScrollDoubleSpinBox()
        preis.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        preis.setRange(0, 999999)
        preis.setDecimals(2)
        preis.setSuffix(" €")
        preis.valueChanged.connect(self._update_summen)
        self.pos_table.setCellWidget(row, 3, preis)

        # MwSt
        mwst = create_mwst_combo()
        mwst.currentIndexChanged.connect(self._update_summen)
        self.pos_table.setCellWidget(row, 4, mwst)

        # §35a
        chk = QCheckBox()
        self.pos_table.setCellWidget(row, 5, chk)

        # Gesamt
        self.pos_table.setItem(row, 6, QTableWidgetItem("0,00 €"))

        # X-Button zum Entfernen
        btn_remove = QPushButton("X")
        btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_remove.setToolTip("Position entfernen")
        btn_remove.setStyleSheet(
            "QPushButton {"
            "  color: #dc2626; background: #fee2e2; border: 1px solid #fca5a5;"
            "  border-radius: 4px; font-size: 14px; font-weight: bold;"
            "  padding: 2px 6px;"
            "}"
            "QPushButton:hover { background: #fecaca; border-color: #f87171; }"
            "QPushButton:pressed { background: #fca5a5; }"
        )
        btn_remove.clicked.connect(lambda _, r=row: self._remove_position_row(r))
        self.pos_table.setCellWidget(row, 7, btn_remove)

        self._update_position_table_height()
        self._update_summen()

    def _remove_position_row(self, row: int):
        if row < self.pos_table.rowCount():
            self.pos_table.removeRow(row)
            # Reconnect X-buttons with updated row indices
            for r in range(self.pos_table.rowCount()):
                btn = self.pos_table.cellWidget(r, 7)
                if isinstance(btn, QPushButton):
                    btn.clicked.disconnect()
                    btn.clicked.connect(lambda _, r=r: self._remove_position_row(r))
                combo = self.pos_table.cellWidget(r, 0)
                if isinstance(combo, QComboBox):
                    try:
                        combo.currentIndexChanged.disconnect()
                    except RuntimeError:
                        pass
                    combo.currentIndexChanged.connect(lambda _, r=r: self._on_article_selected(r))
            self._update_position_table_height()
            self._update_summen()

    def _on_article_selected(self, row: int):
        combo = self.pos_table.cellWidget(row, 0)
        if not isinstance(combo, QComboBox):
            return
        article_id = combo.currentData()
        if article_id:
            article = self.article_repo.get_by_id(article_id)
            if article:
                self.pos_table.item(row, 1).setText(article.bezeichnung)
                preis_widget = self.pos_table.cellWidget(row, 3)
                if isinstance(preis_widget, QDoubleSpinBox):
                    preis_widget.setValue(article.preis)
                mwst_widget = self.pos_table.cellWidget(row, 4)
                if isinstance(mwst_widget, QComboBox):
                    for i in range(mwst_widget.count()):
                        if mwst_widget.itemData(i) == article.mwst:
                            mwst_widget.setCurrentIndex(i)
                            break
                chk_widget = self.pos_table.cellWidget(row, 5)
                if isinstance(chk_widget, QCheckBox):
                    chk_widget.setChecked(article.beguenstigt_35a)
                self._update_summen()

    def _toggle_rabatt(self, checked: bool):
        self.rabatt_widget.setVisible(checked)
        if not checked:
            self.inp_rabatt_wert.setValue(0)
        self._update_summen()

    def _get_positionen_data(self) -> list[dict]:
        positionen = []
        for row in range(self.pos_table.rowCount()):
            menge_w = self.pos_table.cellWidget(row, 2)
            preis_w = self.pos_table.cellWidget(row, 3)
            mwst_w = self.pos_table.cellWidget(row, 4)
            chk_w = self.pos_table.cellWidget(row, 5)

            menge = menge_w.value() if isinstance(menge_w, QDoubleSpinBox) else 1.0
            preis = preis_w.value() if isinstance(preis_w, QDoubleSpinBox) else 0.0
            mwst = mwst_w.currentData() if isinstance(mwst_w, QComboBox) else 19.0
            b35a = chk_w.isChecked() if isinstance(chk_w, QCheckBox) else False

            gesamt = berechne_position(menge, preis)
            positionen.append({
                "gesamt_netto": gesamt,
                "mwst": mwst,
                "beguenstigt_35a": b35a,
            })

            # Update row total
            item = self.pos_table.item(row, 6)
            if item:
                item.setText(f"{gesamt:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))

        return positionen

    def _update_summen(self, *_):
        positionen = self._get_positionen_data()

        rabatt_typ = None
        rabatt_wert = 0.0
        if self.chk_rabatt.isChecked():
            rabatt_typ = "prozent" if self.rb_prozent.isChecked() else "betrag"
            rabatt_wert = self.inp_rabatt_wert.value()

        summen = berechne_rechnung(positionen, rabatt_typ, rabatt_wert)

        fmt = lambda v: f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

        self.lbl_netto.setText(f"Nettobetrag: {fmt(summen.netto)}")

        if summen.rabatt_betrag > 0:
            self.lbl_rabatt.setText(f"Rabatt: −{fmt(summen.rabatt_betrag)}")
            self.lbl_netto_nach_rabatt.setText(f"Netto nach Rabatt: {fmt(summen.netto_nach_rabatt)}")
            self.lbl_rabatt.setVisible(True)
            self.lbl_netto_nach_rabatt.setVisible(True)
        else:
            self.lbl_rabatt.setVisible(False)
            self.lbl_netto_nach_rabatt.setVisible(False)

        mwst_parts = []
        for satz, betrag in sorted(summen.mwst_details.items()):
            mwst_parts.append(f"zzgl. {satz:.0f}% MwSt: {fmt(betrag)}")
        self.lbl_mwst.setText("\n".join(mwst_parts) if mwst_parts else "MwSt: 0,00 €")

        self.lbl_brutto.setText(f"Bruttobetrag: {fmt(summen.brutto)}")

        # §35a-Anteil: Summe aller Positionen mit beguenstigt_35a
        betrag_35a = sum(p["gesamt_netto"] for p in positionen if p["beguenstigt_35a"])
        self.lbl_35a.setText(fmt(betrag_35a))

    def _clear_form(self):
        self.current_invoice = None
        self.cmb_supplier.setCurrentIndex(0)
        self.cmb_customer.setCurrentIndex(0)
        self.inp_rechnungsnr.clear()
        self.inp_datum.setDate(QDate.currentDate())
        self.inp_zahlungsziel.setValue(14)
        self.inp_betreff.clear()
        self.inp_objekt.clear()
        self.inp_ausfuehrung.setDate(self.inp_ausfuehrung.minimumDate())
        self.inp_zeitraum.clear()
        self.pos_table.setRowCount(0)
        self._update_position_table_height()
        self.chk_rabatt.setChecked(False)
        self.inp_rabatt_wert.setValue(0)
        self.lbl_35a.setText("0,00 €")
        self.inp_dankessatz.clear()
        self.inp_hinweise.clear()
        self._update_summen()

    def _read_invoice(self) -> Invoice | None:
        supplier_id = self.cmb_supplier.currentData()
        customer_id = self.cmb_customer.currentData()

        if not supplier_id:
            show_error(self, "Bitte wählen Sie einen Rechnungssteller aus.")
            return None
        if not customer_id:
            show_error(self, "Bitte wählen Sie einen Kunden aus.")
            return None

        rechnungsnr = self.inp_rechnungsnr.text().strip()
        if not rechnungsnr:
            self._generate_number()
            rechnungsnr = self.inp_rechnungsnr.text().strip()

        if self.pos_table.rowCount() == 0:
            show_error(self, "Bitte fügen Sie mindestens eine Position hinzu.")
            return None

        inv = self.current_invoice or Invoice()
        inv.supplier_id = supplier_id
        inv.customer_id = customer_id
        inv.rechnungsnr = rechnungsnr
        inv.datum = date(
            self.inp_datum.date().year(),
            self.inp_datum.date().month(),
            self.inp_datum.date().day(),
        )
        inv.zahlungsziel = self.inp_zahlungsziel.value()
        inv.betreff = self.inp_betreff.text().strip() or None
        inv.objekt_weg = self.inp_objekt.text().strip() or None
        # Ausführungsdatum nur übernehmen wenn vom User gesetzt (nicht Minimum)
        if self.inp_ausfuehrung.date() != self.inp_ausfuehrung.minimumDate():
            d = self.inp_ausfuehrung.date()
            inv.ausfuehrungsdatum = date(d.year(), d.month(), d.day())
        else:
            inv.ausfuehrungsdatum = None
        inv.zeitraum = self.inp_zeitraum.text().strip() or None
        # §35a wird automatisch aus Positionen berechnet
        inv.lohnanteil_35a = 0.0
        inv.geraeteanteil_35a = 0.0
        inv.dankessatz = self.inp_dankessatz.toPlainText().strip() or None
        inv.hinweise = self.inp_hinweise.toPlainText().strip() or None

        if self.chk_rabatt.isChecked():
            inv.rabatt_typ = "prozent" if self.rb_prozent.isChecked() else "betrag"
            inv.rabatt_wert = self.inp_rabatt_wert.value()
        else:
            inv.rabatt_typ = None
            inv.rabatt_wert = 0.0

        # Positionen
        inv.positionen = []
        for row in range(self.pos_table.rowCount()):
            line = InvoiceLine()
            line.position = row + 1

            combo = self.pos_table.cellWidget(row, 0)
            if isinstance(combo, QComboBox):
                line.article_id = combo.currentData()

            item = self.pos_table.item(row, 1)
            beschreibung = item.text() if item else ""
            # Wenn keine Beschreibung aber Freitext im Artikel-Feld, diesen verwenden
            if not beschreibung and isinstance(combo, QComboBox) and not combo.currentData():
                beschreibung = combo.currentText().strip()
            line.beschreibung = beschreibung

            menge_w = self.pos_table.cellWidget(row, 2)
            line.menge = menge_w.value() if isinstance(menge_w, QDoubleSpinBox) else 1.0

            preis_w = self.pos_table.cellWidget(row, 3)
            line.einzelpreis = preis_w.value() if isinstance(preis_w, QDoubleSpinBox) else 0.0

            mwst_w = self.pos_table.cellWidget(row, 4)
            line.mwst = mwst_w.currentData() if isinstance(mwst_w, QComboBox) else 19.0

            chk_w = self.pos_table.cellWidget(row, 5)
            line.beguenstigt_35a = chk_w.isChecked() if isinstance(chk_w, QCheckBox) else False

            line.berechne_gesamt()
            inv.positionen.append(line)

        # Summen berechnen
        pos_data = [
            {"gesamt_netto": l.gesamt_netto, "mwst": l.mwst, "beguenstigt_35a": l.beguenstigt_35a}
            for l in inv.positionen
        ]
        summen = berechne_rechnung(pos_data, inv.rabatt_typ, inv.rabatt_wert)
        inv.netto = summen.netto
        inv.mwst_betrag = summen.mwst_gesamt
        inv.brutto = summen.brutto

        # §35a: Summe der begünstigten Positionen als Lohnanteil speichern
        inv.lohnanteil_35a = sum(
            l.gesamt_netto for l in inv.positionen if l.beguenstigt_35a
        )
        inv.geraeteanteil_35a = 0.0

        return inv

    def on_new(self):
        self._clear_form()

    def on_save(self):
        inv = self._read_invoice()
        if not inv:
            return

        if inv.id:
            self.invoice_repo.update(inv)
            show_success(self, f"Rechnung {inv.rechnungsnr} aktualisiert.")
        else:
            inv.id = self.invoice_repo.create(inv)
            self.current_invoice = inv
            show_success(self, f"Rechnung {inv.rechnungsnr} gespeichert.")

    def _export_pdf(self):
        inv = self._read_invoice()
        if not inv:
            return

        # Save first
        if inv.id:
            self.invoice_repo.update(inv)
        else:
            inv.id = self.invoice_repo.create(inv)
            self.current_invoice = inv

        try:
            from export.pdf_generator import generate_pdf
            supplier = self.supplier_repo.get_by_id(inv.supplier_id)
            customer = self.customer_repo.get_by_id(inv.customer_id)
            pdf_path = generate_pdf(inv, supplier, customer)

            zugferd_embedded = False

            # ZUGFeRD einbetten falls aktiviert
            if self.chk_zugferd.isChecked():
                try:
                    from export.zugferd_generator import generate_zugferd_pdf
                    generate_zugferd_pdf(inv, supplier, customer, pdf_path)
                    zugferd_embedded = True
                except ImportError:
                    show_error(self, "factur-x Bibliothek nicht installiert.\npip install factur-x")
                    return
                except Exception as e:
                    show_error(self, f"ZUGFeRD-Einbettung fehlgeschlagen: {e}\nPDF wurde ohne ZUGFeRD gespeichert.")

            self.invoice_repo.update_pdf_path(inv.id, str(pdf_path))
            inv.pdf_path = str(pdf_path)

            if inv.status == "entwurf":
                self.invoice_repo.update_status(inv.id, "versendet")
                inv.status = "versendet"

            suffix = " (mit ZUGFeRD)" if zugferd_embedded else ""
            show_success(self, f"PDF exportiert{suffix}: {pdf_path}")

            import os
            os.startfile(str(pdf_path))
        except Exception as e:
            show_error(self, f"PDF-Export fehlgeschlagen: {e}")

    def load_invoice(self, invoice: Invoice):
        """Lädt eine bestehende Rechnung in das Formular (z.B. aus dem Archiv)."""
        self.current_invoice = invoice
        self._refresh_dropdowns()

        # Supplier
        idx = self.cmb_supplier.findData(invoice.supplier_id)
        if idx >= 0:
            self.cmb_supplier.setCurrentIndex(idx)

        # Customer
        idx = self.cmb_customer.findData(invoice.customer_id)
        if idx >= 0:
            self.cmb_customer.setCurrentIndex(idx)

        self.inp_rechnungsnr.setText(invoice.rechnungsnr)
        if invoice.datum:
            self.inp_datum.setDate(QDate(invoice.datum.year, invoice.datum.month, invoice.datum.day))
        self.inp_zahlungsziel.setValue(invoice.zahlungsziel)
        self.inp_betreff.setText(invoice.betreff or "")
        self.inp_objekt.setText(invoice.objekt_weg or "")
        if invoice.ausfuehrungsdatum:
            self.inp_ausfuehrung.setDate(QDate(
                invoice.ausfuehrungsdatum.year,
                invoice.ausfuehrungsdatum.month,
                invoice.ausfuehrungsdatum.day,
            ))
        else:
            self.inp_ausfuehrung.setDate(self.inp_ausfuehrung.minimumDate())
        self.inp_zeitraum.setText(invoice.zeitraum or "")

        # Rabatt
        if invoice.rabatt_typ and invoice.rabatt_wert > 0:
            self.chk_rabatt.setChecked(True)
            if invoice.rabatt_typ == "prozent":
                self.rb_prozent.setChecked(True)
            else:
                self.rb_betrag.setChecked(True)
            self.inp_rabatt_wert.setValue(invoice.rabatt_wert)
        else:
            self.chk_rabatt.setChecked(False)

        # §35a wird automatisch aus Positionen berechnet
        self.inp_dankessatz.setPlainText(invoice.dankessatz or "")
        self.inp_hinweise.setPlainText(invoice.hinweise or "")

        # Positionen
        self.pos_table.setRowCount(0)
        self._update_position_table_height()
        for line in invoice.positionen:
            self._add_position_row()
            row = self.pos_table.rowCount() - 1

            combo = self.pos_table.cellWidget(row, 0)
            if isinstance(combo, QComboBox):
                combo.blockSignals(True)
                if line.article_id:
                    idx = combo.findData(line.article_id)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                elif line.beschreibung:
                    combo.setEditText(line.beschreibung)
                combo.blockSignals(False)

            self.pos_table.item(row, 1).setText(line.beschreibung)

            menge_w = self.pos_table.cellWidget(row, 2)
            if isinstance(menge_w, QDoubleSpinBox):
                menge_w.setValue(line.menge)

            preis_w = self.pos_table.cellWidget(row, 3)
            if isinstance(preis_w, QDoubleSpinBox):
                preis_w.setValue(line.einzelpreis)

            mwst_w = self.pos_table.cellWidget(row, 4)
            if isinstance(mwst_w, QComboBox):
                for i in range(mwst_w.count()):
                    if mwst_w.itemData(i) == line.mwst:
                        mwst_w.setCurrentIndex(i)
                        break

            chk_w = self.pos_table.cellWidget(row, 5)
            if isinstance(chk_w, QCheckBox):
                chk_w.setChecked(line.beguenstigt_35a)

        self._update_position_table_height()
        self._update_summen()

