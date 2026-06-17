from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from app.ui.auth_widgets import AuthBrandPanel, make_window_adjustable


LICENSE_THEME = {
    "radius": "8px",
    "radius_sm": "5px",
    "bg": "#f0f4f8",
    "surface": "#f8fafc",
    "card": "#ffffff",
    "accent": "#0071bc",
    "accent_dark": "#005a96",
    "accent_deep": "#004578",
    "text": "#1a2d3d",
    "text_muted": "#64748b",
    "border": "#d0dce8",
    "input_bg": "#ffffff",
}


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = LICENSE_THEME.copy()
        self.setWindowTitle("License Authorization")
        self.setModal(True)
        make_window_adjustable(self, 900, 520, 720, 420)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.brand_panel = AuthBrandPanel(
            "Eswatini GIS\nAuthorization",
            "License-controlled access for protected municipal cadastre and valuation workflows.",
            self.theme,
        )

        self.form_panel = QFrame()
        self.form_panel.setObjectName("FormPanel")
        form_layout = QVBoxLayout(self.form_panel)
        form_layout.setContentsMargins(44, 42, 44, 36)
        form_layout.setSpacing(14)

        header = QLabel("License Authorization")
        header.setObjectName("Header")
        subtitle = QLabel("Authorize this workstation before accessing municipal GIS records.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)

        card = QFrame()
        card.setObjectName("LicenseCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(12)

        self.label = QLabel("Enter your license key")
        self.label.setObjectName("InputLabel")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Example: TEST-1234")
        self.input.setClearButtonEnabled(True)
        self.btn = QPushButton("Activate")
        self.btn.setObjectName("PrimaryButton")
        self.btn.setCursor(Qt.PointingHandCursor)

        self.hint_label = QLabel("A valid license is required before registration or sign in.")
        self.hint_label.setObjectName("HintLabel")
        self.hint_label.setWordWrap(True)

        card_layout.addWidget(self.label)
        card_layout.addWidget(self.input)
        card_layout.addWidget(self.btn)
        card_layout.addWidget(self.hint_label)

        form_layout.addWidget(header)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(8)
        form_layout.addWidget(card)
        form_layout.addStretch()

        root.addWidget(self.brand_panel, 1)
        root.addWidget(self.form_panel, 1)

        self.input.returnPressed.connect(self.btn.click)
        self._apply_styles()

    def _apply_styles(self):
        theme = self.theme
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['bg']};
                color: {theme['text']};
            }}
            QFrame#BrandPanel {{
                background-color: {theme['accent_deep']};
                border: none;
            }}
            QLabel#BrandTitle {{
                color: #ffffff;
                font-size: 29px;
                font-weight: 800;
                line-height: 1.15;
            }}
            QLabel#BrandSubtitle {{
                color: #dbeafe;
                font-size: 12px;
                line-height: 1.45;
            }}
            QFrame#FormPanel {{
                background-color: {theme['card']};
                border-left: 1px solid {theme['border']};
            }}
            QLabel#Header {{
                color: {theme['accent_deep']};
                font-size: 24px;
                font-weight: 800;
            }}
            QLabel#Subtitle, QLabel#HintLabel {{
                color: {theme['text_muted']};
                font-size: 11px;
                line-height: 1.35;
            }}
            QFrame#LicenseCard {{
                background-color: {theme['card']};
                border: 1px solid {theme['border']};
                border-radius: {theme['radius']};
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
        """)
