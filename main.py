from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.license_dialog import LicenseDialog
from app.licensing.license_checker import is_license_valid, activate_license
import sys


def main():
    app = QApplication(sys.argv)

    # Check license
    if not is_license_valid():
        dialog = LicenseDialog()
        dialog.btn.clicked.connect(lambda: try_activate(dialog))
        dialog.exec()

        if not is_license_valid():
            print("License invalid. Exiting.")
            return

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

def try_activate(dialog):
    key = dialog.input.text()
    if activate_license(key):
        dialog.accept()
    else:
        dialog.label.setText("Invalid key. Try again.")

if __name__ == "__main__":
    main()
