from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
)

from PyQt6.QtGui import (
    QFont,
)

from PyQt6.QtCore import QSize, Qt

import pycromanager

class Messages:
    micro_sec_title = "Micromanager"
    connecting_to_micro = "Trying to connect to Micromanager on port 4827"
    not_connected_to_micro = "Not connected"
    button_label_connect_to_micro = "Connect to Micromanager"

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
        pycroVLayout.addWidget(self.connectToPycroButton)

        hlayout.addWidget(pycroWidget)

        widget = QWidget()
        widget.setLayout(hlayout)

        self.setCentralWidget(widget)
    
    def pycroConnectButtonClicked(self):
        print("clicked")


if __name__ == "__main__":
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()