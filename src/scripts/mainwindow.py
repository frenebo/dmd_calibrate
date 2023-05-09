import os

from PyQt6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget
)
from PyQt6.QtGui import QFont

from .deviceinterfaces import (
    PycroInterface,
    StandInPycroInterface,
    PycroConnectionError,
    StandInRaspiInterface,
    RaspiInterface,
    RaspiConnectionError
)
from .dialogs import (
    DmdCalibrationDialog,
    RaspiCredsDialog,
    ErrorDialog
)
from .constants import Messages


class MainWindow(QMainWindow):
    def __init__(self, workdir, useStandIns=False):
        super().__init__()
        self.workdir = workdir
        self.useStandIns = useStandIns

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
        self.calibrateDmdGeometryButton.clicked.connect(self.calibrateDmdButtonClicked)
        topVLayout.addWidget(self.calibrateDmdGeometryButton)
        
        topLevelVWidget = QWidget()
        topLevelVWidget.setLayout(topVLayout)

        self.setCentralWidget(topLevelVWidget)

        self.pycroInterface = None
        self.raspiInterface = None
    
    def calibrateDmdButtonClicked(self):
        print("Calibrating dmd")
        dmdcalibrationdialog = DmdCalibrationDialog(self.pycroInterface, self.raspiInterface, usingStandins=self.useStandIns)
        dmdcalibrationdialog.exec()

        
    def pycroConnectButtonClicked(self):
        try:
            if self.useStandIns:
                self.pycroInterface = StandInPycroInterface()
            else:
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
            
            dlg = ErrorDialog(Messages.connection_failed_title, Messages.micro_connection_failed + ": " + str(e))
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
            dlg = ErrorDialog(Messages.invalid_field_title, fielderr)
            dlg.exec()
            return
        
        try:
            raspiworkdirpath = os.path.join(self.workdir, "raspifiles")
            if self.useStandIns:
                self.raspiInterface = StandInRaspiInterface(hostname, username, password, raspiworkdirpath)
            else:
                self.raspiInterface = RaspiInterface(hostname, username, password, raspiworkdirpath)
            
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
            
            dlg = ErrorDialog(Messages.connection_failed_title, Messages.raspi_connection_failed + ": " + str(e))
            dlg.exec()
        
        self.updateOptions()
    
    def updateOptions(self):
        if self.pycroInterface is not None:

        # if self.raspiInterface is not None and self.pycroInterface is not None:
            self.calibrateDmdGeometryButton.setEnabled(True)
        else:
            self.calibrateDmdGeometryButton.setEnabled(False)
