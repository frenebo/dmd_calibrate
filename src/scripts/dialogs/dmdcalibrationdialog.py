
import pyqtgraph as pg

from PyQt6.QtWidgets import (
    QPushButton,
    QLabel,
    QVBoxLayout,
    QDialog,
    QLineEdit,
)

from .errordialog import ErrorDialog
from ..constants import Messages

class DmdCalibrationDialog(QDialog):
    def __init__(self, pycroInterface, raspiInterface):
        super().__init__()
        pg.setConfigOptions(antialias=True)

        self.setWindowTitle("Dmd Calibration")

        self.vlayout = QVBoxLayout()

        exposureMsLabel = QLabel(Messages.exposure_ms_label)
        self.vlayout.addWidget(exposureMsLabel)
        self.exposureMsWidget = QLineEdit()
        self.exposureMsWidget.setText("100")
        self.vlayout.addWidget(self.exposureMsWidget)

        self.beginButton = QPushButton(Messages.begin)
        self.beginButton.clicked.connect(self.begin_button_clicked)

        self.vlayout.addWidget(self.beginButton)
        
        self.statusLabel = QLabel("")
        self.vlayout.addWidget(self.statusLabel)

        self.setLayout(self.vlayout)
        
        self.pycroInterface = pycroInterface
        self.raspiInterface = raspiInterface

    def begin_button_clicked(self):
        widgetTxt = self.exposureMsWidget.text()
        
        try:
            exposureFlt = float(widgetTxt)
        except ValueError:
            dlg = ErrorDialog(Messages.invalid_field_title, "Can't parse '{}' as floating point number".format(widgetTxt))
            dlg.exec()
            return
        
        if exposureFlt <= 0:
            dlg = ErrorDialog(Messages.invalid_field_title, "Exposure must be greater than zero - invalid value '{}'".format(widgetTxt))
            dlg.exec()
            return
        
        self.exposureMsWidget.setEnabled(False)
        self.beginButton.setEnabled(False)
        
        self.calibrate(exposureFlt)
    
    def show_status(self, status_text):
        self.statusLabel.setText(status_text)

    def calibrate(self, exposure_ms):
        self.show_status(Messages.displaying_colon + Messages.solid_field_image_at_full_brightness)
        
        self.pycroInterface.set_imaging_settings_for_acquisition(
            multishutter_preset="NoMembers",
            sapphire_on_override="on",
            exposure_ms=exposure_ms,
            sapphire_setpoint="110",
            )
        pic = self.pycroInterface.snap_pic()

        imv = pg.ImageView()
        imv.setImage(pic)
        imv.getHistogramWidget()
        
        self.vlayout.addWidget(imv)

        print("took pic!")

