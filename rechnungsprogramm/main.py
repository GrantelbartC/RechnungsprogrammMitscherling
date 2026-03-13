import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from db.database import Database
from services.ai_config import load_local_env
from ui.main_window import MainWindow


def main():
    load_local_env()

    app = QApplication(sys.argv)
    app.setApplicationName("Rechnungsprogramm")
    app.setOrganizationName("Rechnungsprogramm")

    db = Database.get_instance()
    db.initialize()

    window = MainWindow(db)
    window.show()

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
