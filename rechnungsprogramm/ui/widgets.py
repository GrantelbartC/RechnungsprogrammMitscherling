from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt, QDate, QEvent


class NoScrollSpinBox(QSpinBox):
    """QSpinBox die das Scrollrad ignoriert wenn nicht fokussiert."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox die das Scrollrad ignoriert wenn nicht fokussiert."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class NoScrollDateEdit(QDateEdit):
    """QDateEdit die das Scrollrad ignoriert wenn nicht fokussiert."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class FormCard(QGroupBox):
    """Karte mit Rahmen und Titel für Formularsektionen."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(10)
        self.form_layout.setContentsMargins(16, 20, 16, 16)
        self.setLayout(self.form_layout)

    def add_field(self, label: str, widget: QWidget):
        self.form_layout.addRow(label, widget)
        return widget

    def add_row(self, widget: QWidget):
        self.form_layout.addRow(widget)
        return widget


class LabeledField(QWidget):
    """Label + Eingabefeld vertikal gestapelt."""

    def __init__(self, label: str, widget: QWidget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(label)
        lbl.setProperty("cssClass", "secondary")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        self.widget = widget


class SearchBar(QWidget):
    """Suchleiste mit Eingabefeld."""

    def __init__(self, placeholder: str = "Suchen...", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        layout.addWidget(self.search_input)

    @property
    def text(self) -> str:
        return self.search_input.text()


class StatusBadge(QLabel):
    """Farbiges Status-Badge."""

    STATUS_CLASSES = {
        "entwurf": "badge-warn",
        "versendet": "badge-primary",
        "bezahlt": "badge-success",
    }

    STATUS_LABELS = {
        "entwurf": "Entwurf",
        "versendet": "Versendet",
        "bezahlt": "Bezahlt",
    }

    def __init__(self, status: str = "entwurf", parent=None):
        super().__init__(parent)
        self.set_status(status)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_status(self, status: str):
        css_class = self.STATUS_CLASSES.get(status, "badge-warn")
        label = self.STATUS_LABELS.get(status, status)
        self.setText(label)
        self.setProperty("cssClass", css_class)
        self.style().unpolish(self)
        self.style().polish(self)


def confirm_delete(parent: QWidget, item_name: str = "diesen Eintrag") -> bool:
    reply = QMessageBox.question(
        parent,
        "Löschen bestätigen",
        f"Möchten Sie {item_name} wirklich löschen?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def show_success(parent: QWidget, message: str):
    QMessageBox.information(parent, "Erfolg", message)


def show_error(parent: QWidget, message: str):
    QMessageBox.critical(parent, "Fehler", message)


def create_date_edit(default_today: bool = True) -> NoScrollDateEdit:
    date_edit = NoScrollDateEdit()
    date_edit.setCalendarPopup(True)
    date_edit.setDisplayFormat("dd.MM.yyyy")
    if default_today:
        date_edit.setDate(QDate.currentDate())
    return date_edit


def create_currency_spinbox(max_val: float = 999999.99) -> NoScrollDoubleSpinBox:
    spinbox = NoScrollDoubleSpinBox()
    spinbox.setRange(0, max_val)
    spinbox.setDecimals(2)
    spinbox.setSuffix(" €")
    spinbox.setLocale(spinbox.locale())
    return spinbox


def create_mwst_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("19%", 19.0)
    combo.addItem("7%", 7.0)
    combo.addItem("0%", 0.0)
    return combo


def create_anrede_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("", "")
    combo.addItems(["Herr", "Frau", "Firma", "Diverse"])
    return combo
