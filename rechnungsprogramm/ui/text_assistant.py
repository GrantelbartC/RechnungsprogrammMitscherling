from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db.database import Database
from db.repos.customer_repo import CustomerRepo
from db.repos.supplier_repo import SupplierRepo
from services.ai_config import load_ai_preferences
from services.ai_prompt_builder import LetterContext
from ui.ai_workers import GenerateLetterWorker
from ui.widgets import FormCard, show_error, show_success


class TextAssistantTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.customer_repo = CustomerRepo(db)
        self.supplier_repo = SupplierRepo(db)
        self._ai_thread: QThread | None = None
        self._ai_worker: GenerateLetterWorker | None = None
        self._pending_action = "generate"

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        title = QLabel("Textassistent")
        title.setProperty("cssClass", "heading")
        self.main_layout.addWidget(title)

        subtitle = QLabel(
            "Nutze freie Anweisungen fuer Geschaeftsschreiben und uebernimm den Entwurf bei Bedarf direkt "
            "in den Firmenschreiben-Tab. Optionaler Kunden-, Firmen- und Entwurfskontext wird beruecksichtigt."
        )
        subtitle.setProperty("cssClass", "secondary")
        subtitle.setWordWrap(True)
        self.main_layout.addWidget(subtitle)

        self._build_prompt_area()
        self._build_result_area()

        self.main_layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_prompt_area(self):
        card = FormCard("Anweisung")

        self.cmb_supplier = QComboBox()
        card.add_field("Rechnungssteller (optional)", self.cmb_supplier)

        self.cmb_customer = QComboBox()
        card.add_field("Kunde (optional)", self.cmb_customer)

        tone_layout = QHBoxLayout()
        self.cmb_tone = QComboBox()
        self.cmb_tone.addItem("Neutral", "neutral")
        self.cmb_tone.addItem("Freundlich", "freundlich")
        self.cmb_tone.addItem("Foermlich", "foermlich")
        tone_layout.addWidget(self.cmb_tone)

        self.chk_structured = QCheckBox("Strenges Antwortformat (JSON) anfordern")
        self.chk_structured.setChecked(True)
        self.chk_structured.setToolTip(
            "Empfohlen fuer eine zuverlaessige Aufteilung in Betreff, Anrede, Brieftext und Grussformel."
        )
        tone_layout.addWidget(self.chk_structured)
        tone_layout.addStretch()

        tone_widget = QWidget()
        tone_widget.setLayout(tone_layout)
        card.add_field("Stil und Format", tone_widget)

        context_layout = QHBoxLayout()
        self.chk_customer_context = QCheckBox("Kundendaten einbeziehen")
        self.chk_customer_context.setChecked(True)
        self.chk_customer_context.setToolTip("Verwendet Empfaengerdaten und eine passende Anrede als Kontext.")
        context_layout.addWidget(self.chk_customer_context)

        self.chk_supplier_context = QCheckBox("Firmendaten einbeziehen")
        self.chk_supplier_context.setChecked(True)
        self.chk_supplier_context.setToolTip("Verwendet Absenderdaten und den moeglichen Unterzeichner als Kontext.")
        context_layout.addWidget(self.chk_supplier_context)
        context_layout.addStretch()

        context_widget = QWidget()
        context_widget.setLayout(context_layout)
        card.add_row(context_widget)

        hint = QLabel(
            "Tipp: Gute Ergebnisse entstehen, wenn Anlass, Ziel, Fristen und Ton klar benannt sind. "
            "Beispiel: Bitte erinnere freundlich an ein fehlendes Feedback zum Angebot und schlage ein kurzes Telefonat vor."
        )
        hint.setProperty("cssClass", "secondary")
        hint.setWordWrap(True)
        card.add_row(hint)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setMinimumHeight(180)
        self.prompt_edit.setPlaceholderText(
            "z. B. Formuliere ein sachliches Anschreiben zur Terminverschiebung, "
            "entschuldige die kurzfristige Aenderung und nenne zwei neue Vorschlaege."
        )
        card.add_row(self.prompt_edit)

        self.lbl_status = QLabel("")
        self.lbl_status.setProperty("cssClass", "secondary")
        self.lbl_status.setWordWrap(True)
        card.add_row(self.lbl_status)

        button_layout = QHBoxLayout()
        self.btn_generate = QPushButton("Entwurf erstellen")
        self.btn_generate.setProperty("cssClass", "primary")
        self.btn_generate.setToolTip("Erstellt einen neuen KI-Entwurf aus deiner Anweisung.")
        self.btn_generate.clicked.connect(self._generate)
        button_layout.addWidget(self.btn_generate)

        self.btn_regenerate = QPushButton("Neu formulieren")
        self.btn_regenerate.setToolTip("Setzt denselben Inhalt einmal neu auf.")
        self.btn_regenerate.clicked.connect(lambda: self._revise("Formuliere den Entwurf neu."))
        button_layout.addWidget(self.btn_regenerate)

        self.btn_shorter = QPushButton("Kompakter")
        self.btn_shorter.setToolTip("Strafft den bestehenden Entwurf, ohne Inhalte zu verlieren.")
        self.btn_shorter.clicked.connect(lambda: self._revise("Verkuerze den Entwurf, ohne wichtige Inhalte zu verlieren."))
        button_layout.addWidget(self.btn_shorter)

        self.btn_formal = QPushButton("Formeller")
        self.btn_formal.setToolTip("Macht den Ton formeller und sachlicher.")
        self.btn_formal.clicked.connect(lambda: self._revise("Formuliere den Entwurf formeller und geschaeftlicher."))
        button_layout.addWidget(self.btn_formal)

        self.btn_friendly = QPushButton("Freundlicher")
        self.btn_friendly.setToolTip("Macht den Ton etwas waermer und zugewandter.")
        self.btn_friendly.clicked.connect(lambda: self._revise("Formuliere den Entwurf etwas freundlicher und zugewandter."))
        button_layout.addWidget(self.btn_friendly)
        button_layout.addStretch()

        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        card.add_row(button_widget)

        self.main_layout.addWidget(card)
        self._set_revision_enabled(False)

    def _build_result_area(self):
        card = FormCard("Entwurf")

        info = QLabel("Alle Felder bleiben editierbar, bevor du sie in Firmenschreiben uebernimmst.")
        info.setProperty("cssClass", "secondary")
        info.setWordWrap(True)
        card.add_row(info)

        self.inp_betreff = QLineEdit()
        card.add_field("Betreff", self.inp_betreff)

        self.inp_anrede = QLineEdit()
        card.add_field("Anrede", self.inp_anrede)

        self.inp_brieftext = QTextEdit()
        self.inp_brieftext.setAcceptRichText(False)
        self.inp_brieftext.setMinimumHeight(220)
        card.add_field("Brieftext", self.inp_brieftext)

        self.inp_grussformel = QLineEdit()
        card.add_field("Grussformel", self.inp_grussformel)

        button_layout = QHBoxLayout()
        self.btn_send_to_fs = QPushButton("In Firmenschreiben uebernehmen")
        self.btn_send_to_fs.setProperty("cssClass", "primary")
        self.btn_send_to_fs.setToolTip("Uebernimmt den aktuellen Entwurf in den Firmenschreiben-Tab.")
        self.btn_send_to_fs.clicked.connect(self._send_to_firmenschreiben)
        button_layout.addWidget(self.btn_send_to_fs)

        self.btn_clear = QPushButton("Leeren")
        self.btn_clear.clicked.connect(self._clear_result)
        button_layout.addWidget(self.btn_clear)
        button_layout.addStretch()

        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        card.add_row(button_widget)

        self.main_layout.addWidget(card)
        self.btn_send_to_fs.setEnabled(False)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_dropdowns()
        self._apply_preferences()

    def _refresh_dropdowns(self):
        current_supplier = self.cmb_supplier.currentData()
        self.cmb_supplier.blockSignals(True)
        self.cmb_supplier.clear()
        self.cmb_supplier.addItem("-- Kein Kontext --", None)
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
        self.cmb_customer.addItem("-- Kein Kontext --", None)
        for customer in self.customer_repo.get_all():
            self.cmb_customer.addItem(customer.display_name, customer.id)
        if current_customer is not None:
            idx = self.cmb_customer.findData(current_customer)
            if idx >= 0:
                self.cmb_customer.setCurrentIndex(idx)
        self.cmb_customer.blockSignals(False)

    def _apply_preferences(self):
        preferences = load_ai_preferences()
        self.chk_customer_context.setChecked(preferences.include_customer_context)
        self.chk_supplier_context.setChecked(preferences.include_supplier_context)
        self.chk_structured.setChecked(preferences.structured_output)

        tone_index = self.cmb_tone.findData(preferences.default_tone)
        if tone_index >= 0:
            self.cmb_tone.setCurrentIndex(tone_index)

    def _generate(self):
        self._start_ai_request()

    def _revise(self, instruction: str):
        self._start_ai_request(revision_instruction=instruction)

    def _start_ai_request(self, revision_instruction: str | None = None):
        if self._ai_thread and self._ai_thread.isRunning():
            return

        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            show_error(self, "Bitte zuerst einen Prompt eingeben.")
            return

        worker = GenerateLetterWorker(
            prompt=prompt,
            context=self._build_context(),
            tone=self.cmb_tone.currentData(),
            structured=self.chk_structured.isChecked(),
            revision_instruction=revision_instruction,
            current_draft=self._current_draft(),
        )

        self._ai_thread = QThread(self)
        self._ai_worker = worker
        self._pending_action = "revise" if revision_instruction else "generate"
        worker.moveToThread(self._ai_thread)
        self._ai_thread.started.connect(worker.run)
        worker.finished.connect(self._on_ai_success)
        worker.failed.connect(self._on_ai_error)
        worker.finished.connect(self._cleanup_ai_thread)
        worker.failed.connect(self._cleanup_ai_thread)

        if revision_instruction:
            self._set_busy(True, "KI ueberarbeitet den Entwurf...")
        else:
            self._set_busy(True, "KI erstellt einen Entwurf...")
        self._ai_thread.start()

    def _cleanup_ai_thread(self, *_):
        if self._ai_thread:
            self._ai_thread.quit()
            self._ai_thread.wait()
            self._ai_thread.deleteLater()
            self._ai_thread = None
        if self._ai_worker:
            self._ai_worker.deleteLater()
            self._ai_worker = None
        self._set_busy(False, self.lbl_status.text())

    def _on_ai_success(self, data: dict):
        self.inp_betreff.setText(data.get("betreff", ""))
        self.inp_anrede.setText(data.get("anrede", ""))
        self.inp_brieftext.setPlainText(data.get("brieftext", ""))
        self.inp_grussformel.setText(data.get("grussformel", ""))
        self._set_revision_enabled(True)
        self.btn_send_to_fs.setEnabled(True)
        if self._pending_action == "revise":
            self.lbl_status.setText("Entwurf ueberarbeitet.")
        else:
            self.lbl_status.setText("Entwurf erstellt.")

    def _on_ai_error(self, message: str):
        self.lbl_status.setText("")
        show_error(self, message)

    def _set_busy(self, busy: bool, message: str):
        self.btn_generate.setEnabled(not busy)
        self.btn_regenerate.setEnabled(not busy and self._has_result())
        self.btn_shorter.setEnabled(not busy and self._has_result())
        self.btn_formal.setEnabled(not busy and self._has_result())
        self.btn_friendly.setEnabled(not busy and self._has_result())
        self.btn_send_to_fs.setEnabled(not busy and self._has_result())
        self.lbl_status.setText(message)

    def _set_revision_enabled(self, enabled: bool):
        self.btn_regenerate.setEnabled(enabled)
        self.btn_shorter.setEnabled(enabled)
        self.btn_formal.setEnabled(enabled)
        self.btn_friendly.setEnabled(enabled)

    def _has_result(self) -> bool:
        return any(
            field.strip()
            for field in (
                self.inp_betreff.text(),
                self.inp_anrede.text(),
                self.inp_brieftext.toPlainText(),
                self.inp_grussformel.text(),
            )
        )

    def _clear_result(self):
        self.inp_betreff.clear()
        self.inp_anrede.clear()
        self.inp_brieftext.clear()
        self.inp_grussformel.clear()
        self.btn_send_to_fs.setEnabled(False)
        self._set_revision_enabled(False)
        self.lbl_status.setText("")

    def on_new(self):
        self.prompt_edit.clear()
        self._clear_result()

    def on_search(self):
        self.prompt_edit.setFocus()

    def _current_draft(self) -> dict[str, str]:
        return {
            "betreff": self.inp_betreff.text().strip(),
            "anrede": self.inp_anrede.text().strip(),
            "brieftext": self.inp_brieftext.toPlainText().strip(),
            "grussformel": self.inp_grussformel.text().strip(),
        }

    def _build_context(self) -> LetterContext | None:
        context = LetterContext()

        if self.chk_supplier_context.isChecked():
            supplier = self._selected_supplier()
            if supplier:
                context.supplier_name = supplier.firma or ""
                context.supplier_signatory = supplier.inhaber or supplier.firma or ""
                context.supplier_contact = " | ".join(
                    part
                    for part in [
                        supplier.strasse,
                        f"{supplier.plz or ''} {supplier.ort or ''}".strip(),
                        supplier.telefon,
                        supplier.email,
                    ]
                    if part
                )

        if self.chk_customer_context.isChecked():
            customer = self._selected_customer()
            if customer:
                context.customer_name = customer.display_name
                context.customer_company = customer.firma or ""
                context.customer_contact = " | ".join(
                    part
                    for part in [
                        customer.strasse,
                        f"{customer.plz or ''} {customer.ort or ''}".strip(),
                        customer.telefon,
                        customer.email,
                    ]
                    if part
                )
                context.suggested_salutation = self._build_anrede(customer)

        current_draft = self._current_draft()
        context.current_subject = current_draft["betreff"]
        context.current_salutation = current_draft["anrede"]
        context.current_body = current_draft["brieftext"]
        context.current_closing = current_draft["grussformel"]

        if any(
            [
                context.supplier_name,
                context.supplier_contact,
                context.customer_name,
                context.customer_contact,
                context.suggested_salutation,
                context.current_subject,
                context.current_salutation,
                context.current_body,
                context.current_closing,
            ]
        ):
            return context
        return None

    def _selected_customer(self):
        customer_id = self.cmb_customer.currentData()
        return self.customer_repo.get_by_id(customer_id) if customer_id else None

    def _selected_supplier(self):
        supplier_id = self.cmb_supplier.currentData()
        return self.supplier_repo.get_by_id(supplier_id) if supplier_id else None

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

    def _send_to_firmenschreiben(self):
        if not self._has_result():
            show_error(self, "Es gibt noch keinen Entwurf zum Uebernehmen.")
            return

        main_window = self.window()
        if not hasattr(main_window, "fs_tab") or not hasattr(main_window, "tabs"):
            show_error(self, "Firmenschreiben ist im Hauptfenster nicht verfuegbar.")
            return

        fs_tab = main_window.fs_tab
        if hasattr(fs_tab, "refresh_contexts"):
            fs_tab.refresh_contexts()

        supplier_id = self.cmb_supplier.currentData()
        if supplier_id:
            idx = fs_tab.cmb_supplier.findData(supplier_id)
            if idx >= 0:
                fs_tab.cmb_supplier.setCurrentIndex(idx)

        customer_id = self.cmb_customer.currentData()
        if customer_id:
            idx = fs_tab.cmb_customer.findData(customer_id)
            if idx >= 0:
                fs_tab.cmb_customer.setCurrentIndex(idx)

        fs_tab.apply_generated_text(self._current_draft())
        main_window.tabs.setCurrentWidget(fs_tab)
        if hasattr(main_window, "set_status"):
            main_window.set_status("KI-Entwurf in Firmenschreiben uebernommen.")
        show_success(self, "Der KI-Entwurf wurde in Firmenschreiben uebernommen.")
