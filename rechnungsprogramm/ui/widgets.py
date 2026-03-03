from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QFormLayout,
    QCalendarWidget, QDialog,
)
from PySide6.QtCore import Qt, QDate, QEvent, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator


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


class OptionalDateInput(QWidget):
    """Optionales Datumsfeld mit Texteingabe und Kalender-Popup."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._minimum_date = QDate(1752, 9, 14)
        self._date = self._minimum_date

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.input = QLineEdit()
        self.input.setPlaceholderText("TT.MM.JJJJ")
        self.input.setMaxLength(10)
        self.input.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^(\d{0,2})(\.\d{0,2})?(\.\d{0,4})?$"),
                self.input,
            )
        )
        self.input.editingFinished.connect(self._commit_text)
        layout.addWidget(self.input)

        self.btn_calendar = QPushButton("...")
        self.btn_calendar.setFixedWidth(32)
        self.btn_calendar.setToolTip("Kalender oeffnen")
        self.btn_calendar.clicked.connect(self._open_calendar)
        layout.addWidget(self.btn_calendar)

        self.calendar_popup = QDialog(self, Qt.WindowType.Popup)
        popup_layout = QVBoxLayout(self.calendar_popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        self.calendar = QCalendarWidget(self.calendar_popup)
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self._on_calendar_selected)
        popup_layout.addWidget(self.calendar)

    def minimumDate(self) -> QDate:
        return self._minimum_date

    def date(self) -> QDate:
        self._commit_text()
        return self._date

    def setDate(self, qdate: QDate):
        if not qdate or not qdate.isValid() or qdate == self._minimum_date:
            self._date = self._minimum_date
            self.input.clear()
            return

        self._date = qdate
        self.input.setText(qdate.toString("dd.MM.yyyy"))

    def _commit_text(self):
        text = self.input.text().strip()

        if not text:
            self._date = self._minimum_date
            self.input.clear()
            return

        parsed = QDate.fromString(text, "dd.MM.yyyy")
        if parsed.isValid():
            self.setDate(parsed)
            return

        # Ungueltig: letztes gueltiges Datum wiederherstellen.
        if self._date == self._minimum_date:
            self.input.clear()
        else:
            self.input.setText(self._date.toString("dd.MM.yyyy"))

    def _open_calendar(self):
        current = self._date if self._date != self._minimum_date else QDate.currentDate()
        self.calendar.setSelectedDate(current)
        self.calendar.setCurrentPage(current.year(), current.month())
        popup_pos = self.mapToGlobal(self.rect().bottomLeft())
        self.calendar_popup.move(popup_pos)
        self.calendar_popup.show()
        self.calendar.setFocus()

    def _on_calendar_selected(self, selected: QDate):
        self.setDate(selected)
        self.calendar_popup.hide()


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


def create_optional_date_input() -> OptionalDateInput:
    return OptionalDateInput()


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
