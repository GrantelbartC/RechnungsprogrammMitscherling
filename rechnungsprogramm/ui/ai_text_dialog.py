from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.ai_config import load_ai_preferences
from services.ai_prompt_builder import LetterContext
from ui.ai_workers import GenerateLetterWorker
from ui.widgets import FormCard, show_error


class AITextDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mit KI formulieren")
        self.resize(860, 720)

        self._supplier = None
        self._customer = None
        self._draft = {}
        self._accept_mode = "all"
        self._ai_thread: QThread | None = None
        self._ai_worker: GenerateLetterWorker | None = None
        self._pending_action = "generate"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        info = QLabel(
            "Beschreibe Anlass, Ziel und Ton des Schreibens. "
            "Optionaler Firmen-, Kunden- und Entwurfskontext wird beruecksichtigt. "
            "Das Ergebnis bleibt voll editierbar."
        )
        info.setProperty("cssClass", "secondary")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._build_prompt_card(layout)
        self._build_result_card(layout)
        self._build_footer(layout)

        self._apply_preferences()
        self._set_accept_buttons_enabled(False)

    def _build_prompt_card(self, parent_layout: QVBoxLayout):
        card = FormCard("Anweisung")

        tone_layout = QHBoxLayout()
        self.cmb_tone = QComboBox()
        self.cmb_tone.addItem("Neutral", "neutral")
        self.cmb_tone.addItem("Freundlich", "freundlich")
        self.cmb_tone.addItem("Foermlich", "foermlich")
        tone_layout.addWidget(self.cmb_tone)

        self.chk_structured = QCheckBox("Strenges Antwortformat (JSON) anfordern")
        self.chk_structured.setChecked(True)
        self.chk_structured.setToolTip(
            "Empfohlen fuer eine zuverlaessige Uebernahme in Betreff, Anrede, Brieftext und Grussformel."
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
            "Tipp: Nenne Anlass, Ziel, noetige Fristen und den gewuenschten Ton. "
            "Beispiel: Formuliere eine kurze Absage fuer einen Montagstermin und biete zwei Alternativen in der kommenden Woche an."
        )
        hint.setProperty("cssClass", "secondary")
        hint.setWordWrap(True)
        card.add_row(hint)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setMinimumHeight(160)
        self.prompt_edit.setPlaceholderText(
            "z. B. Bitte entschuldige die Lieferverzoegerung, erklaere den Grund knapp "
            "und schlage einen neuen Termin vor."
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

        parent_layout.addWidget(card)

    def _build_result_card(self, parent_layout: QVBoxLayout):
        card = FormCard("Entwurf")

        info = QLabel("Du kannst alle Felder vor der Uebernahme manuell anpassen.")
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

        parent_layout.addWidget(card)

    def _build_footer(self, parent_layout: QVBoxLayout):
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        self.btn_body_only = QPushButton("Nur Brieftext uebernehmen")
        self.btn_body_only.setToolTip("Uebernimmt nur den Brieftext in das aktuelle Firmenschreiben.")
        self.btn_body_only.clicked.connect(self._accept_body_only)
        footer_layout.addWidget(self.btn_body_only)

        self.btn_accept = QPushButton("Kompletten Entwurf uebernehmen")
        self.btn_accept.setToolTip("Uebernimmt Betreff, Anrede, Brieftext und Grussformel.")
        self.btn_accept.setProperty("cssClass", "primary")
        self.btn_accept.clicked.connect(self._accept_all)
        footer_layout.addWidget(self.btn_accept)

        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        parent_layout.addLayout(footer_layout)

    def set_context(self, supplier=None, customer=None, draft: dict[str, str] | None = None):
        self._supplier = supplier
        self._customer = customer
        self._draft = draft or {}
        self._set_result_fields(self._draft)
        has_draft = any((value or "").strip() for value in self._draft.values())
        self._set_accept_buttons_enabled(has_draft)
        if has_draft:
            self.lbl_status.setText("Vorhandener Entwurf als Ausgangspunkt geladen.")
        else:
            self.lbl_status.setText("")

    def get_generated_data(self) -> dict[str, str]:
        return {
            "betreff": self.inp_betreff.text().strip(),
            "anrede": self.inp_anrede.text().strip(),
            "brieftext": self.inp_brieftext.toPlainText().strip(),
            "grussformel": self.inp_grussformel.text().strip(),
        }

    def get_accept_mode(self) -> str:
        return self._accept_mode

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
            current_draft=self.get_generated_data(),
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
        self._set_result_fields(data)
        self._set_accept_buttons_enabled(True)
        if self._pending_action == "revise":
            self.lbl_status.setText("Entwurf ueberarbeitet.")
        else:
            self.lbl_status.setText("Entwurf erstellt.")

    def _on_ai_error(self, message: str):
        self.lbl_status.setText("")
        show_error(self, message)

    def _set_result_fields(self, data: dict[str, str]):
        self.inp_betreff.setText((data.get("betreff") or "").strip())
        self.inp_anrede.setText((data.get("anrede") or "").strip())
        self.inp_brieftext.setPlainText((data.get("brieftext") or "").strip())
        self.inp_grussformel.setText((data.get("grussformel") or "").strip())

    def _set_busy(self, busy: bool, message: str):
        has_result = self._has_result()
        self.btn_generate.setEnabled(not busy)
        self.btn_shorter.setEnabled(not busy and has_result)
        self.btn_formal.setEnabled(not busy and has_result)
        self.btn_friendly.setEnabled(not busy and has_result)
        self.btn_accept.setEnabled(not busy and has_result)
        self.btn_body_only.setEnabled(not busy and has_result)
        self.lbl_status.setText(message)

    def _set_accept_buttons_enabled(self, enabled: bool):
        self.btn_accept.setEnabled(enabled)
        self.btn_body_only.setEnabled(enabled)
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

    def _build_context(self) -> LetterContext | None:
        context = LetterContext()

        if self.chk_supplier_context.isChecked() and self._supplier:
            context.supplier_name = self._supplier.firma or ""
            context.supplier_signatory = self._supplier.inhaber or self._supplier.firma or ""
            context.supplier_contact = " | ".join(
                part
                for part in [
                    self._supplier.strasse,
                    f"{self._supplier.plz or ''} {self._supplier.ort or ''}".strip(),
                    self._supplier.telefon,
                    self._supplier.email,
                ]
                if part
            )

        if self.chk_customer_context.isChecked() and self._customer:
            context.customer_name = self._customer.display_name
            context.customer_company = self._customer.firma or ""
            context.customer_contact = " | ".join(
                part
                for part in [
                    self._customer.strasse,
                    f"{self._customer.plz or ''} {self._customer.ort or ''}".strip(),
                    self._customer.telefon,
                    self._customer.email,
                ]
                if part
            )
            context.suggested_salutation = _build_anrede(self._customer)

        draft = self.get_generated_data()
        if not any(draft.values()):
            draft = self._draft

        context.current_subject = (draft.get("betreff") or "").strip()
        context.current_salutation = (draft.get("anrede") or "").strip()
        context.current_body = (draft.get("brieftext") or "").strip()
        context.current_closing = (draft.get("grussformel") or "").strip()

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

    def _accept_all(self):
        self._accept_mode = "all"
        self.accept()

    def _accept_body_only(self):
        self._accept_mode = "body_only"
        self.accept()


def _build_anrede(customer) -> str:
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
