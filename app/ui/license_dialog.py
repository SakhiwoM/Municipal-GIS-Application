from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

class LicenseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enter License Key")

        layout = QVBoxLayout()

        self.label = QLabel("Enter your license key:")
        self.input = QLineEdit()
        self.btn = QPushButton("Activate")

        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addWidget(self.btn)

        self.setLayout(layout)
