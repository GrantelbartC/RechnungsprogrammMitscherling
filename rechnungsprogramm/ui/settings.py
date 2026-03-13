from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QHBoxLayout,
)

from services.ai_config import (
    AIPreferences,
    load_ai_config,
    load_ai_preferences,
    resolve_model,
    save_ai_preferences,
)
from ui.widgets import FormCard, NoScrollDoubleSpinBox, NoScrollSpinBox, show_success


class SettingsTab(QWidget):
    def __init__(self, db=None):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Einstellungen")
        title.setProperty("cssClass", "heading")
        layout.addWidget(title)

        info = QLabel(
            "Zugangsdaten werden ausschliesslich aus der .env geladen. "
            "Hier speicherst du nur lokale KI-Standardwerte fuer Stil, Modell-Override und Antwortverhalten."
        )
        info.setProperty("cssClass", "secondary")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.info_card = FormCard("Verbindung")
        self.lbl_provider = QLabel("")
        self.lbl_provider.setWordWrap(True)
        self.info_card.add_field("Provider", self.lbl_provider)

        self.lbl_model_env = QLabel("")
        self.lbl_model_env.setWordWrap(True)
        self.info_card.add_field("Modell aus .env", self.lbl_model_env)

        self.lbl_effective_model = QLabel("")
        self.lbl_effective_model.setWordWrap(True)
        self.info_card.add_field("Aktives Modell", self.lbl_effective_model)

        self.lbl_env_path = QLabel("")
        self.lbl_env_path.setWordWrap(True)
        self.lbl_env_path.setProperty("cssClass", "secondary")
        self.info_card.add_field(".env-Datei", self.lbl_env_path)

        self.lbl_key_status = QLabel("")
        self.info_card.add_field("API-Key", self.lbl_key_status)
        layout.addWidget(self.info_card)

        self.ai_card = FormCard("KI-Standardwerte")
        self.inp_model_override = QLineEdit()
        self.inp_model_override.setPlaceholderText("Optional: Modell aus .env ueberschreiben")
        self.inp_model_override.setToolTip("Leer lassen, um das Modell aus der .env unveraendert zu verwenden.")
        self.ai_card.add_field("Modell-Override", self.inp_model_override)

        self.cmb_tone = QComboBox()
        self.cmb_tone.addItem("Neutral", "neutral")
        self.cmb_tone.addItem("Freundlich", "freundlich")
        self.cmb_tone.addItem("Foermlich", "foermlich")
        self.ai_card.add_field("Standard-Stil", self.cmb_tone)

        self.chk_customer_context = QCheckBox("Kundendaten standardmaessig einbeziehen")
        self.ai_card.add_row(self.chk_customer_context)

        self.chk_supplier_context = QCheckBox("Firmendaten standardmaessig einbeziehen")
        self.ai_card.add_row(self.chk_supplier_context)

        self.chk_structured = QCheckBox("Strenges Antwortformat (JSON) standardmaessig anfordern")
        self.chk_structured.setToolTip("Empfohlen fuer eine saubere Uebernahme in die vier Formularfelder.")
        self.ai_card.add_row(self.chk_structured)

        self.inp_temperature = NoScrollDoubleSpinBox()
        self.inp_temperature.setRange(0.0, 2.0)
        self.inp_temperature.setDecimals(2)
        self.inp_temperature.setSingleStep(0.05)
        self.inp_temperature.setToolTip("Niedriger = konstanter und sachlicher, hoeher = variantenreicher.")
        self.ai_card.add_field("Temperatur", self.inp_temperature)

        self.inp_max_tokens = NoScrollSpinBox()
        self.inp_max_tokens.setRange(100, 4000)
        self.inp_max_tokens.setSingleStep(50)
        self.inp_max_tokens.setToolTip("Begrenzt die maximale Laenge der Modellantwort.")
        self.ai_card.add_field("Max. Tokens", self.inp_max_tokens)

        hint = QLabel(
            "Hinweis: Niedrige Temperatur liefert meist stabilere Geschaeftstexte. "
            "Das JSON-Format ist fuer die automatische Feldzuordnung am zuverlaessigsten."
        )
        hint.setProperty("cssClass", "secondary")
        hint.setWordWrap(True)
        self.ai_card.add_row(hint)
        layout.addWidget(self.ai_card)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_reload = QPushButton("Neu laden")
        self.btn_reload.clicked.connect(self._load_values)
        button_layout.addWidget(self.btn_reload)

        self.btn_save = QPushButton("Speichern")
        self.btn_save.setProperty("cssClass", "primary")
        self.btn_save.clicked.connect(self._save_values)
        button_layout.addWidget(self.btn_save)

        layout.addLayout(button_layout)
        layout.addStretch()

        self._load_values()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_values()

    def _load_values(self):
        config = load_ai_config()
        preferences = load_ai_preferences()

        self.lbl_provider.setText(config.provider or "nvidia")
        self.lbl_model_env.setText(config.model or "-")
        self.lbl_effective_model.setText(resolve_model(config, preferences))
        self.lbl_env_path.setText(config.env_path or "Keine .env-Datei gefunden")
        self.lbl_key_status.setText("vorhanden" if config.api_key else "nicht gefunden")

        self.inp_model_override.setText(preferences.model_override)
        tone_idx = self.cmb_tone.findData(preferences.default_tone)
        if tone_idx >= 0:
            self.cmb_tone.setCurrentIndex(tone_idx)
        self.chk_customer_context.setChecked(preferences.include_customer_context)
        self.chk_supplier_context.setChecked(preferences.include_supplier_context)
        self.chk_structured.setChecked(preferences.structured_output)
        self.inp_temperature.setValue(preferences.temperature)
        self.inp_max_tokens.setValue(preferences.max_tokens)

    def _save_values(self):
        preferences = AIPreferences(
            model_override=self.inp_model_override.text().strip(),
            default_tone=self.cmb_tone.currentData(),
            include_customer_context=self.chk_customer_context.isChecked(),
            include_supplier_context=self.chk_supplier_context.isChecked(),
            structured_output=self.chk_structured.isChecked(),
            temperature=self.inp_temperature.value(),
            max_tokens=self.inp_max_tokens.value(),
        )
        save_ai_preferences(preferences)
        show_success(self, "KI-Einstellungen gespeichert.")
