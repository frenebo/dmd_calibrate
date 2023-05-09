
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

def make_image_flipper(self, np_images, label_str=None, under_label=None):
    np_images = np.array(np_images)
    flipperWidget = QWidget()
    flipVLay = QVBoxLayout()
    flipperWidget.setLayout(flipVLay)
    
    if label_str is not None:
        lab = QLabel(label_str)
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        flipVLay.addWidget(lab)
    
    imgView = pg.ImageView(discreteTimeLine=True)
    imgView.setImage(np_images, axes={ "t": 0, "x": 1, "y": 2 })
    flipVLay.addWidget(imgView)

    if under_label is not None:
        undlab = QLabel(under_label)
        undlab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        flipVLay.addWidget(undlab)
    
    return flipperWidget

class CoordCalibrationDialog(QDialog):
    def __init__(self, pycroInterface, raspiInterface, using_standins=False):
        super().__init__()
        self.setWindowTitle("Dmd Coordinate Calibration")

class BrightnessCalibrationDialog(QDialog):
    def __init__(self, pycroInterface, raspiInterface, using_standins=False):
        super().__init__()
        self.setWindowTitle("Dmd Brightness Calibration")

class DmdCalibrationDialog(QDialog):
    def __init__(self, pycroInterface, raspiInterface, using_standins=False):
        super().__init__()
        pg.setConfigOptions(antialias=True)

        self.setWindowTitle("Dmd Calibration Setup")

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
        self.using_standins = using_standins

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
        self.show_status(Messages.starting_calibration)
        
        solid_bright_pics = None
        solid_dark_pics = None
        bright_level = None
        dark_level = None
        bright_dark_calibration_error = None
        illuminated_section_mask = None
        
        with self.raspiInterface.image_sender() as raspi_image_sender:
            calibrator = Calibrator(self.pycroInterface, raspi_image_sender, exposure_ms, using_standins=self.using_standins)
            calibrator.turn_on_laser_and_setup_pycromanager()
            
            try:
                self.show_status(Messages.calibrating_colon + Messages.solid_bright_field)
                calibrator.calibrate_solid_bright_field()
                solid_bright_pics = calibrator.get_solid_bright_cam_pics()
            
                self.show_status(Messages.calibrating_colon + Messages.solid_dark_field)
                calibrator.calibrate_solid_dark_field()
                solid_dark_pics = calibrator.get_solid_dark_cam_pics()

                calibrator.calculate_bright_and_dark_levels()
                
                bright_level, dark_level = calibrator.get_bright_and_dark_levels()
                illuminated_section_mask = calibrator.get_illuminated_section_mask()
            except CalibrationException as e:
                self.show_status(Messages.calibration_error)
                bright_dark_calibration_error = str(e)
            finally:
                calibrator.turn_off_laser_and_turn_off_shutter()
        
        if solid_bright_pics is not None:
            if bright_level is not None:
                under_label = Messages.bright_level + ": " + str(bright_level)
            else:
                under_label = None
            
            avgBrightFieldVWidg = make_image_flipper(
                solid_bright_pics,
                label_str=Messages.solid_bright_field_calibration_images,
                under_label=under_label
                )
            self.calibrationImagesHLayout.addWidget(avgBrightFieldVWidg)
        
        if solid_dark_pics is not None:
            if dark_level is not None:
                under_label = Messages.dark_level + ": " + str(dark_level)
            else:
                under_label = None
            
            avgDarkFieldVWidg = make_image_flipper(
                solid_dark_pics,
                label_str=Messages.solid_dark_field_calibration_images,
                under_label=under_label
                )
            
            self.calibrationImagesHLayout.addWidget(avgDarkFieldVWidg)
        
        if bright_dark_calibration_error is not None:
            print("Showing calibration error: " + bright_dark_calibration_error)
            dlg = ErrorDialog(Messages.calibration_error, bright_dark_calibration_error)
            dlg.exec()
        else:  
            self.bright_level = bright_level
            self.dark_level = dark_level

            beginCoordCalibrationButton = QPushButton(Messages.button_label_begin_coord_calibration)
            beginCoordCalibrationButton.clicked.connect(self.beginCoordCalibrationButtonClicked)

            self.calibrationImagesHLayout.addWidget(beginCoordCalibrationButton)
    
    def beginCoordCalibrationButtonClicked(self):
        dlg = CoordCalibrationDialog(self.pycroInterface, self.raspiInterface, using_standins=self.using_standins)
        dlg.exec()
