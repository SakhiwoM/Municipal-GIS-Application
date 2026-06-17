from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.license_dialog import LicenseDialog
from app.ui.login_window import run_login
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

    while True:
        session = run_login(data_dir=".")
        if session is None:
            print("Login cancelled or failed. Exiting.")
            return

        window = MainWindow(session=session)
        logout_state = {"requested": False}

        def handle_logout():
            logout_state["requested"] = True
            window.close()
            app.quit()

        window.logout_requested.connect(handle_logout)
        window.show()

        app.exec()
        if not logout_state["requested"]:
            break

    sys.exit(0)

def try_activate(dialog):
    key = dialog.input.text()
    if activate_license(key):
        dialog.accept()
    else:
        dialog.label.setText("Invalid key. Try again.")
        if hasattr(dialog, "hint_label"):
            dialog.hint_label.setText("Check the license key with your GIS administrator, then try again.")

if __name__ == "__main__":
    main()
