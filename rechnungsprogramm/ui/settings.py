from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class SettingsTab(QWidget):
    def __init__(self, db=None):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Einstellungen")
        title.setProperty("cssClass", "heading")
        layout.addWidget(title)
        layout.addWidget(QLabel("Einstellungen werden in Phase 7 implementiert."))
        layout.addStretch()
