
import pyqtgraph as pg
import numpy as np

from PyQt6.QtWidgets import (
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QWidget,
    QLineEdit,
)
# from PyQt6 import QtCore
from PyQt6.QtCore import Qt

from .errordialog import ErrorDialog
from ..constants import Messages, DmdConstants
from ..calibration import Calibrator, CalibrationException

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
        
        calibrationImagesWidget = QWidget()
        self.calibrationImagesHLayout = QHBoxLayout()
        calibrationImagesWidget.setLayout(self.calibrationImagesHLayout)
        self.vlayout.addWidget(calibrationImagesWidget)

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
    
    def make_image_flipper(self, np_images, label_str=None):
        np_images = np.array(np_images)
        VWidg = QWidget()
        VLay = QVBoxLayout()
        VWidg.setLayout(VLay)
        
        if label_str is not None:
            lab = QLabel(label_str)
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            VLay.addWidget(lab)
        
        imgView = pg.ImageView()
        imgView.setImage(np_images, axes={ "t": 0, "x": 1, "y": 2 })
        VLay.addWidget(imgView)
        
        return VWidg
        

    def calibrate(self, exposure_ms):
        self.show_status(Messages.starting_calibration)
        
        solid_bright_pics = None
        solid_dark_pics = None
        bright_level = None
        dark_level = None
        bright_dark_calibration_error = None
        
        with self.raspiInterface.image_sender() as raspi_image_sender:
            calibrator = Calibrator(self.pycroInterface, raspi_image_sender, exposure_ms)
            calibrator.turn_on_laser_and_setup_pycromanager()
            
            try:
                self.show_status(Messages.calibrating_colon + Messages.solid_bright_field)
                calibrator.calibrate_solid_bright_field()
                solid_bright_pics = calibrator.get_solid_bright_cam_pics()
            
                self.show_status(Messages.calibrating_colon + Messages.solid_dark_field)
                calibrator.calibrate_solid_dark_field()
                solid_dark_pics = calibrator.get_solid_dark_cam_pics()
                
                bright_level, dark_level = calibrator.get_bright_and_dark_levels()
            except CalibrationException as e:
                self.show_status(Messages.calibration_error)
                bright_dark_calibration_error = str(e)
            finally:
                calibrator.turn_off_laser_and_turn_off_shutter()
        
        if solid_bright_pics is not None:
            avgBrightFieldVWidg = self.make_image_flipper(
                solid_bright_pics,
                label_str=Messages.solid_bright_field
                )
            self.calibrationImagesHLayout.addWidget(avgBrightFieldVWidg)
        
        if solid_dark_pics is not None:
            avgDarkFieldVWidg = self.make_image_flipper(
                solid_dark_pics,
                label_str=Messages.solid_dark_field
                )
            self.calibrationImagesHLayout.addWidget(avgDarkFieldVWidg)
        
        if bright_dark_calibration_error is not None:
            print("Showing calibration error: " + bright_dark_calibration_error)
            dlg = ErrorDialog(Messages.calibration_error, bright_dark_calibration_error)
            dlg.exec()
        
        
        
        # avgDarkFieldVWidg = QWidget()
        # avgDarkFieldVLay = QVBoxLayout()
        # avgDarkFieldVWidg.setLayout(avgDarkFieldVLay)
        # avgDarkFieldImgView 
        
        # self.calibrationImagesHLayout.addWidget(avgDarkFieldVWidg)
        
        
        # if 
        
        # # pic = self.pycroInterface.snap_pic()

        # imv = pg.ImageView()
        # imv.setImage(pic)
        # imv.getHistogramWidget()
        
        # self.vlayout.addWidget(imv)

        print("took pic!")

