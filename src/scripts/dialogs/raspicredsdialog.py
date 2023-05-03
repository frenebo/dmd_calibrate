
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
    QLineEdit
)
from ..constants import Messages

class RaspiCredsDialog(QDialog):
    def __init__(self):
        super().__init__()
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.accept)
        
        self.layout = QVBoxLayout()
        message = QLabel(Messages.enter_raspi_ssh_login_creds)
        
        self.hostnameWidget = QLineEdit()
        self.hostnameWidget.setPlaceholderText("hostname")
        self.usernameWidget = QLineEdit()
        self.usernameWidget.setPlaceholderText("username")
        self.passwordWidget = QLineEdit()
        self.passwordWidget.setPlaceholderText("password")
        
        self.layout.addWidget(message)
        self.layout.addWidget(self.hostnameWidget)
        self.layout.addWidget(self.usernameWidget)
        self.layout.addWidget(self.passwordWidget)
        self.layout.addWidget(self.buttonBox)
        
        self.setLayout(self.layout)

