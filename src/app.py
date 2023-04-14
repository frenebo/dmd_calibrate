from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QDialogButtonBox,
)

from PyQt6.QtGui import (
    QFont,
)

from PyQt6.QtCore import QSize, Qt

import pycromanager

from scripts.pycrointerface import PycroInterface, PycroConnectionError

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

class ConnectionErrorDialog(QDialog):
    def __init__(self, text):
        super().__init__()

        self.setWindowTitle("Connection Failed")

        
        QBtn = QDialogButtonBox.StandardButton.Ok

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        # self.buttonBox.rejected.connect(self.reject)

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
        raspiVLayout.addWidget(self.raspiStatusLabelWidget)
        
        self.connectToRaspiButton = QPushButton(Messages.button_label_connect_raspi)
        raspiVLayout.addWidget(self.connectToRaspiButton)
        
        hlayout.addWidget(raspiWidget)

        widget = QWidget()
        widget.setLayout(hlayout)

        self.setCentralWidget(widget)

        self.pycroInterface = None
    
    def pycroConnectButtonClicked(self):
        # dlg = ConnectionErrorDialog("asdfasdf")
        # dlg.exec()
        try:
            self.pycroInterface = PycroInterface()

            self.pycroStatusLabelWidget.setText(Messages.connected_to_micro)
        except PycroConnectionError as e:
            dlg = ConnectionErrorDialog(Messages.micro_connection_failed + ": " + str(e))
            dlg.exec()


if __name__ == "__main__":
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()