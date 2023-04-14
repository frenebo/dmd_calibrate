from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QLineEdit,
    QDialogButtonBox,
)

from PyQt6.QtGui import (
    QFont,
)

from PyQt6.QtCore import QSize, Qt

import pycromanager

from scripts.pycrointerface import PycroInterface, PycroConnectionError
from scripts.raspiinterface import RaspiInterface, RaspiConnectionError

class Messages:
    micro_sec_title = "Micromanager"
    connecting_to_micro = "Trying to connect to Micromanager on port 4827"
    not_connected_to_micro = "Not connected"
    connected_to_micro = "Connected"
    button_label_connect_to_micro = "Connect to Micromanager"
    micro_connection_failed = "Micromanager connection failed"
    raspi_sec_title = "Raspi (DMD video source)"
    not_connected_to_raspi = "Not connected"
    button_label_connect_raspi = "Connect to Raspi"
    not_connected_to_raspi = "Not connected"
    raspi_connection_failed = "Raspi connection failed"
    connected_to_raspi = "Connected"
    enter_a_hostname = "Must enter a hostname to proceed"
    enter_a_username = "Must enter a username to proceed"
    enter_a_password = "Must enter a password to proceed"
    button_label_calibrate_dmd = "Calibrate DMD Geometry"

class RaspiCredsDialog(QDialog):
    def __init__(self):
        super().__init__()
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.accept)
        
        self.layout = QVBoxLayout()
        message = QLabel("Enter Raspi SSH login Credentials")
        
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

class ConnectionErrorDialog(QDialog):
    def __init__(self, text):
        super().__init__()

        self.setWindowTitle("Connection Failed")

        QBtn = QDialogButtonBox.StandardButton.Ok

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        message = QLabel(text)
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dmd Acquisition Tool")

        hlayout = QHBoxLayout()

        pycroWidget = QWidget()
        pycroVLayout = QVBoxLayout()
        pycroWidget.setLayout(pycroVLayout)

        pycroTitleWidget = QLabel(Messages.micro_sec_title)
        pycroTitleWidget.setFont(QFont("Arial", 20))
        pycroVLayout.addWidget(pycroTitleWidget)

        self.pycroStatusLabelWidget = QLabel(Messages.not_connected_to_micro)
        self.pycroStatusLabelWidget.setStyleSheet('background-color: yellow')
        pycroVLayout.addWidget(self.pycroStatusLabelWidget)

        self.connectToPycroButton = QPushButton(Messages.button_label_connect_to_micro)
        self.connectToPycroButton.clicked.connect(self.pycroConnectButtonClicked)
        pycroVLayout.addWidget(self.connectToPycroButton)

        hlayout.addWidget(pycroWidget)
        
        raspiWidget = QWidget()
        raspiVLayout = QVBoxLayout()
        raspiWidget.setLayout(raspiVLayout)
        
        raspiTitleWidget = QLabel(Messages.raspi_sec_title)
        raspiTitleWidget.setFont(QFont("Arial", 20))
        raspiVLayout.addWidget(raspiTitleWidget)
        
        self.raspiStatusLabelWidget = QLabel(Messages.not_connected_to_raspi)
        self.raspiStatusLabelWidget.setStyleSheet('background-color: yellow')
        raspiVLayout.addWidget(self.raspiStatusLabelWidget)
        
        self.connectToRaspiButton = QPushButton(Messages.button_label_connect_raspi)
        self.connectToRaspiButton.clicked.connect(self.raspiConnectButtonClicked)
        raspiVLayout.addWidget(self.connectToRaspiButton)
        
        hlayout.addWidget(raspiWidget)
        
        componentMenu = QWidget()
        componentMenu.setLayout(hlayout)
        
        topVLayout = QVBoxLayout()
        topVLayout.addWidget(componentMenu)
        
        self.calibrateDmdGeometryButton = QPushButton(Messages.button_label_calibrate_dmd)
        self.calibrateDmdGeometryButton.setEnabled(False)
        topVLayout.addWidget(self.calibrateDmdGeometryButton)
        
        
        
        topLevelVWidget = QWidget()
        topLevelVWidget.setLayout(topVLayout)

        self.setCentralWidget(topLevelVWidget)

        self.pycroInterface = None
        self.raspiInterface = None
    
    def pycroConnectButtonClicked(self):
        try:
            self.pycroInterface = PycroInterface()
            
            # if success
            self.pycroStatusLabelWidget.setText(Messages.connected_to_micro)
            self.pycroStatusLabelWidget.setStyleSheet('background-color: lightgreen')
            self.connectToPycroButton.setEnabled(False)
            
        except PycroConnectionError as e:
            self.pycroInterface = None
            # if fail
            self.pycroStatusLabelWidget.setText(Messages.not_connected_to_micro)
            self.pycroStatusLabelWidget.setStyleSheet('background-color: yellow')
            self.connectToPycroButton.setEnabled(True)
            
            dlg = ConnectionErrorDialog(Messages.micro_connection_failed + ": " + str(e))
            dlg.exec()
        
        self.updateOptions()
    
    def raspiConnectButtonClicked(self):
        paramdlg = RaspiCredsDialog()
        paramdlg.exec()
        
        hostname = paramdlg.hostnameWidget.text()
        username = paramdlg.usernameWidget.text()
        password = paramdlg.passwordWidget.text()
        
        fielderr = None
        
        if hostname == "":
            fielderr = Messages.enter_a_hostname
        elif username == "":
            fielderr = Messages.enter_a_username
        elif password == "":
            fielderr = Messages.enter_a_password
        
        if fielderr is not None:
            dlg = ConnectionErrorDialog(fielderr)
            dlg.exec()
            return
        
        try:
            self.raspiInterface = RaspiInterface(hostname, username, password)
            
            # if success
            self.raspiStatusLabelWidget.setText(Messages.connected_to_raspi)
            self.raspiStatusLabelWidget.setStyleSheet('background-color: lightgreen')
            self.connectToRaspiButton.setEnabled(False)
        except RaspiConnectionError as e:
            self.raspiInterface = None
            # if fail
            self.raspiStatusLabelWidget.setText(Messages.not_connected_to_raspi)
            self.raspiStatusLabelWidget.setStyleSheet('background-color: yellow')
            self.connectToRaspiButton.setEnabled(True)
            
            dlg = ConnectionErrorDialog(Messages.raspi_connection_failed + ": " + str(e))
            dlg.exec()
        
        self.updateOptions()
    
    def updateOptions(self):
        if self.raspiInterface is not None and self.pycroInterface is not None:
            self.calibrateDmdGeometryButton.setEnabled(True)
        else:
            self.calibrateDmdGeometryButton.setEnabled(False)


if __name__ == "__main__":
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()