from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.licensing.auth_manager import AuthManager, ROLE_DISPLAY
from app.licensing.auth_manager import UserProfile
from app.licensing.license_checker import activate_license
from app.ui.auth_widgets import AuthBrandPanel, make_window_adjustable
from app.ui.license_dialog import LicenseDialog


LOGIN_THEME = {
    "radius": "8px",
    "radius_sm": "5px",
    "bg": "#f0f4f8",
    "surface": "#f8fafc",
    "surface_alt": "#e4ecf6",
    "card": "#ffffff",
    "accent": "#0071bc",
    "accent_dark": "#005a96",
    "accent_deep": "#004578",
    "text": "#1a2d3d",
    "text_muted": "#64748b",
    "border": "#d0dce8",
    "input_bg": "#ffffff",
}


class LoginWindow(QDialog):
    login_successful = Signal(object)
    exit_requested = Signal()

    def __init__(self, auth_manager=None, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager or AuthManager()
        self.session = None
        self.theme = LOGIN_THEME.copy()

        self.setWindowTitle("Eswatini GIS")
        self.setModal(True)
        make_window_adjustable(self, 920, 560, 760, 460)
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.brand_panel = AuthBrandPanel(
            "Eswatini Cadastre\n& Valuation Platform",
            "Secure municipal access for spatial records, valuations, dashboards, and field-ready GIS workflows.",
            self.theme,
        )

        self.form_panel = QFrame()
        self.form_panel.setObjectName("FormPanel")
        form_layout = QVBoxLayout(self.form_panel)
        form_layout.setContentsMargins(44, 42, 44, 36)
        form_layout.setSpacing(14)

        form_title = QLabel("Sign in")
        form_title.setObjectName("FormTitle")
        form_subtitle = QLabel("")
        form_subtitle.setObjectName("FormSubtitle")
        form_layout.addWidget(form_title)
        form_layout.addWidget(form_subtitle)
        form_layout.addSpacing(10)

        form_layout.addWidget(self._make_input_label("USERNAME"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setClearButtonEnabled(True)
        form_layout.addWidget(self.username_input)

        form_layout.addWidget(self._make_input_label("PASSWORD"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_input)

        self.message_label = QLabel("")
        self.message_label.setObjectName("MessageLabel")
        self.message_label.setWordWrap(True)
        form_layout.addWidget(self.message_label)

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("PrimaryButton")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._attempt_login)
        form_layout.addWidget(self.login_btn)

        self.register_btn = QPushButton("Register first-time access")
        self.register_btn.setObjectName("SecondaryButton")
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.clicked.connect(self._open_registration)
        form_layout.addWidget(self.register_btn)

        secondary_row = QHBoxLayout()
        self.help_btn = QPushButton("Forgot password?")
        self.help_btn.setObjectName("LinkButton")
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.clicked.connect(self._show_help)
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("SecondaryButton")
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.clicked.connect(self._exit)
        secondary_row.addWidget(self.help_btn)
        secondary_row.addStretch()
        secondary_row.addWidget(self.exit_btn)
        form_layout.addLayout(secondary_row)
        form_layout.addStretch()

        self.org_label = QLabel("Eswatini Municipal Authority")
        self.org_label.setObjectName("OrgLabel")
        form_layout.addWidget(self.org_label)

        root.addWidget(self.brand_panel, 1)
        root.addWidget(self.form_panel, 1)

        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self._attempt_login)

    def _make_stat(self, value, label):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        value_lbl = QLabel(value)
        value_lbl.setObjectName("StatValue")
        label_lbl = QLabel(label)
        label_lbl.setObjectName("StatLabel")
        layout.addWidget(value_lbl)
        layout.addWidget(label_lbl)
        return widget

    def _make_input_label(self, text):
        label = QLabel(text)
        label.setObjectName("InputLabel")
        return label

    @staticmethod
    def _style_sheet_for(theme):
        return f"""
            QDialog {{
                background-color: {theme['bg']};
                color: {theme['text']};
            }}
            QFrame#BrandPanel {{
                background-color: {theme['accent_deep']};
                background-image: url("C:/Users/Colani/Documents/GitHub/Municipal-GIS-Application-main/app/ui/Flag-map_of_Eswatini.png");
                background-repeat: no-repeat;
                background-position: center;
                border: none;
            }}
            QLabel#Badge {{
                color: #0000ff;
                border:none;
                border-radius: {theme['radius_sm']};
                padding: 6px 10px;
                font-size: 10px;
                font-weight: 800;
            }}
            QLabel#BrandTitle {{
                color: #000000;
                font-size: 29px;
                font-weight: 800;
                line-height: 1.15;
            }}
            QLabel#BrandSubtitle {{
                color: #dbeafe;
                font-size: 12px;
                line-height: 1.45;
            }}
            QLabel#StatValue {{
                color: #000000;
                font-size: 16px;
                font-weight: 800;
            }}
            QLabel#StatLabel {{
                color: #000000;
                font-size: 9px;
                font-weight: 700;
            }}
            QFrame#FormPanel {{
                background-color: {theme['card']};
                border-left: 1px solid {theme['border']};
            }}
            QLabel#FormTitle {{
                color: {theme['accent_deep']};
                font-size: 26px;
                font-weight: 800;
            }}
            QLabel#FormSubtitle, QLabel#OrgLabel {{
                color: {theme['text_muted']};
                font-size: 11px;
            }}
            QLabel#InputLabel {{
                color: {theme['text_muted']};
                font-size: 9px;
                font-weight: 800;
            }}
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                border-radius: {theme['radius_sm']};
                padding: 10px 12px;
                font-size: 12px;
                min-height: 22px;
            }}
            QLineEdit:focus {{
                border-color: {theme['accent']};
                background-color: {theme['surface']};
            }}
            QLabel#MessageLabel {{
                color: #b91c1c;
                font-size: 11px;
                min-height: 28px;
            }}
            QPushButton#PrimaryButton {{
                background-color: {theme['accent']};
                color: #ffffff;
                border: 1px solid {theme['accent_dark']};
                border-radius: {theme['radius_sm']};
                padding: 11px 16px;
                font-size: 12px;
                font-weight: 800;
            }}
            QPushButton#PrimaryButton:hover {{
                background-color: {theme['accent_dark']};
            }}
            QPushButton#SecondaryButton {{
                background-color: {theme['surface_alt']};
                color: {theme['accent_deep']};
                border: 1px solid {theme['border']};
                border-radius: {theme['radius_sm']};
                padding: 8px 14px;
                font-weight: 700;
            }}
            QPushButton#SecondaryButton:hover {{
                background-color: {theme['surface']};
                border-color: {theme['accent']};
            }}
            QPushButton#LinkButton {{
                background-color: transparent;
                color: {theme['accent']};
                border: none;
                text-align: left;
                font-size: 11px;
                font-weight: 700;
                padding: 8px 0;
            }}
            QPushButton#LinkButton:hover {{
                color: {theme['accent_dark']};
            }}
        """

    def _apply_styles(self):
        self.setStyleSheet(self._style_sheet_for(self.theme))

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username:
            self._set_message("Wrong username.")
            self.username_input.setFocus()
            return
        if not password:
            self._set_message("Wrong password.")
            self.password_input.setFocus()
            return

        ok, message = self.auth_manager.authenticate(username, password)
        if not ok:
            self._set_message(message)
            self.password_input.clear()
            self.password_input.setFocus()
            return

        self.session = self.auth_manager.get_current_session()
        role_name = ROLE_DISPLAY.get(self.session.role, self.session.role)
        self._set_message(f"{message} Role: {role_name}.", success=True)
        self.login_successful.emit(self.session)
        self.accept()

    def _set_message(self, message, success=False):
        color = "#047857" if success else "#b91c1c"
        self.message_label.setStyleSheet(f"color: {color}; font-size: 11px; min-height: 28px;")
        self.message_label.setText(message)

    def _show_help(self):
        QMessageBox.information(
            self,
            "Account Recovery",
            "Contact your GIS administrator or support@eswatini-gis.gov.sz to reset your municipal GIS password.",
        )

    def _open_registration(self):
        license_dialog = LicenseDialog(parent=self)
        license_dialog.btn.clicked.connect(lambda: self._attempt_registration_license(license_dialog))
        if license_dialog.exec() != QDialog.Accepted:
            self._set_message("License authorization is required before first-time registration.")
            return

        dialog = RegistrationDialog(auth_manager=self.auth_manager, parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.created_username:
            self.username_input.setText(dialog.created_username)
            self.password_input.clear()
            self.password_input.setFocus()
            self._set_message("Registration complete. Sign in with your new account.", success=True)

    def _attempt_registration_license(self, dialog):
        key = dialog.input.text().strip()
        if activate_license(key):
            dialog.accept()
            return
        dialog.label.setText("Invalid license key.")
        dialog.hint_label.setText("A valid license key is required before a first-time account can be created.")
        dialog.input.setFocus()

    def _exit(self):
        self.exit_requested.emit()
        self.reject()


class RegistrationDialog(QDialog):
    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.created_username = None
        self.theme = LOGIN_THEME.copy()

        self.setWindowTitle("First-Time Registration")
        self.setModal(True)
        make_window_adjustable(self, 980, 680, 780, 560)
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.brand_panel = AuthBrandPanel(
            "First-Time\nRegistration",
            "Authorize, identify, and create a secure viewer profile for the Eswatini municipal GIS workspace.",
            self.theme,
        )

        self.form_panel = QFrame()
        self.form_panel.setObjectName("FormPanel")
        layout = QVBoxLayout(self.form_panel)
        layout.setContentsMargins(44, 32, 44, 30)
        layout.setSpacing(10)

        title = QLabel("Register access")
        title.setObjectName("FormTitle")
        subtitle = QLabel("Create a viewer account for first-time access to the Eswatini GIS platform.")
        subtitle.setObjectName("FormSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        layout.addWidget(self._make_input_label("FULL NAME"))
        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("Enter your full name")
        layout.addWidget(self.full_name_input)

        layout.addWidget(self._make_input_label("USERNAME"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        self.username_input.setClearButtonEnabled(True)
        layout.addWidget(self.username_input)

        layout.addWidget(self._make_input_label("EMAIL"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("name@organization.gov.sz")
        layout.addWidget(self.email_input)

        layout.addWidget(self._make_input_label("ORGANIZATION"))
        self.organization_input = QLineEdit()
        self.organization_input.setPlaceholderText("Municipality or department")
        self.organization_input.setText("Eswatini Municipal Authority")
        layout.addWidget(self.organization_input)

        layout.addWidget(self._make_input_label("PASSWORD"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Create a password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        layout.addWidget(self._make_input_label("CONFIRM PASSWORD"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_input)

        self.role_note = QLabel("New registrations are created as Viewer accounts. An administrator can upgrade permissions after verification.")
        self.role_note.setObjectName("FormSubtitle")
        self.role_note.setWordWrap(True)
        layout.addWidget(self.role_note)

        self.message_label = QLabel("")
        self.message_label.setObjectName("MessageLabel")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.submit_btn = QPushButton("Create Account")
        self.submit_btn.setObjectName("PrimaryButton")
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self._register)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addWidget(self.cancel_btn)
        button_row.addStretch()
        button_row.addWidget(self.submit_btn)
        layout.addLayout(button_row)

        root.addWidget(self.brand_panel, 1)
        root.addWidget(self.form_panel, 1)

        self.full_name_input.returnPressed.connect(self.username_input.setFocus)
        self.username_input.returnPressed.connect(self.email_input.setFocus)
        self.email_input.returnPressed.connect(self.organization_input.setFocus)
        self.organization_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.confirm_input.setFocus)
        self.confirm_input.returnPressed.connect(self._register)

    def _make_input_label(self, text):
        label = QLabel(text)
        label.setObjectName("InputLabel")
        return label

    def _apply_styles(self):
        self.setStyleSheet(LoginWindow._style_sheet_for(self.theme))

    def _register(self):
        full_name = self.full_name_input.text().strip()
        username = self.username_input.text().strip().lower()
        email = self.email_input.text().strip()
        organization = self.organization_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if not full_name:
            self._set_message("Full name is required.")
            self.full_name_input.setFocus()
            return
        if len(username) < 3:
            self._set_message("Username must be at least 3 characters.")
            self.username_input.setFocus()
            return
        if self.auth_manager.get_user(username):
            self._set_message("That username already exists.")
            self.username_input.setFocus()
            return
        if "@" not in email or "." not in email:
            self._set_message("Enter a valid email address.")
            self.email_input.setFocus()
            return
        if not organization:
            self._set_message("Organization is required.")
            self.organization_input.setFocus()
            return
        if len(password) < 8:
            self._set_message("Password must be at least 8 characters.")
            self.password_input.setFocus()
            return
        if password != confirm:
            self._set_message("Passwords do not match.")
            self.confirm_input.clear()
            self.confirm_input.setFocus()
            return

        profile = UserProfile(
            username=username,
            password_hash=AuthManager.hash_password(password),
            role="viewer",
            full_name=full_name,
            organization=organization,
            email=email,
        )
        if not self.auth_manager.add_user(profile):
            self._set_message("Unable to create account. Try another username.")
            return

        self.created_username = username
        self.accept()

    def _set_message(self, message):
        self.message_label.setText(message)


def run_login(data_dir="."):
    auth_manager = AuthManager(data_dir=data_dir)
    dialog = LoginWindow(auth_manager=auth_manager)
    if dialog.exec() == QDialog.Accepted:
        return dialog.session
    return None