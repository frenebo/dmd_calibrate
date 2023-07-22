
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

def make_image_flipper(np_images, label_str=None, under_label=None):
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


def draw_white_circle(np_float_img, diameter, center_x, center_y):
    assert np_float_img.dtype == float, "Image should be float array"
    assert int(diameter) == diameter, "Diameter value should be integer"
    assert int(center_x) == center_x, "Center x value should be integer"
    assert int(center_y) == center_y, "Center y value should be integer"
    assert diameter > 0, "Diameter should be positive"
    assert diameter % 2 == 1, "Diameter should be odd, so the circle will be centered on a single pixel"

    diameter = int(diameter)
    center_x = int(center_x)
    center_y = int(center_y)

    circ_xx, circ_yy = np.meshgrid(np.arange(diameter), np.arange(diameter))

    # This should already be a whole number, but casting to an integer so we can array index with it
    rad = int((diameter - 1) / 2)

    circ_mask = (np.square(circ_xx - rad) + np.square(circ_yy - rad)) <= np.square(rad + 0.5)

    # Convert to float
    circ_mask  = circ_mask.astype(float)

    np_float_img[center_y - rad:center_y + rad + 1, center_x - rad:center_x + rad + 1] += circ_mask

    # If the spot wasn't already white, then it'll have brightness more than 1.0 now - fix this here
    np_float_img[np_float_img > 1.0] = 1.0


class CoordCalibrationDialog(QDialog):
    def __init__(self, pycroInterface, raspiInterface, calibrator, exposureMs):
        super().__init__()
        self.setWindowTitle("Dmd Coordinate Calibration")

        self.pycroInterface = pycroInterface
        self.raspiInterface = raspiInterface
        self.exposureMs = exposureMs
        # self.usingStandins = usingStandins
        self.calibrator = calibrator

        self.vlayout = QVBoxLayout()
        
        self.statusLabel = QLabel("")
        self.vlayout.addWidget(self.statusLabel)

        self.setLayout(self.vlayout)

        self.calibrate()
    
    def calibrate(self):
        self.show_status(Messages.starting_calibration)
        
        self.calibrator.take_coord_calibration_data()
        self.calibrator.calculate_coord_calibration()
        
        # @TODO For checking the model's error, make sure that the actual measurements are far apart
        # @TODO enough for the error to mean something. If all the measurements are clustered to one
        # @TODO point, any model will give a good result, but something is probably wrong.s
        pass

    def show_status(self, status_text):
        self.statusLabel.setText(status_text)

class BrightnessCalibrationDialog(QDialog):
    def __init__(self, pycroInterface, raspiInterface, calibrator, exposureMs):
        super().__init__()

        self.pycroInterface = pycroInterface
        self.raspiInterface = raspiInterface
        self.exposureMs = exposureMs
        # self.usingStandins = usingStandins
        self.calibrator = calibrator

        self.setWindowTitle("Dmd Brightness Calibration")

        self.vlayout = QVBoxLayout()

        calibrationImagesWidget = QWidget()
        self.calibrationImagesHLayout = QHBoxLayout()
        calibrationImagesWidget.setLayout(self.calibrationImagesHLayout)
        self.vlayout.addWidget(calibrationImagesWidget)

        self.statusLabel = QLabel("")
        self.vlayout.addWidget(self.statusLabel)

        self.setLayout(self.vlayout)
        

        self.calibrate()

        
    def show_status(self, status_text):
        self.statusLabel.setText(status_text)

    def calibrate(self):
        self.show_status(Messages.starting_calibration)
        
        solid_bright_pics = None
        solid_dark_pics = None
        bright_dark_calibration_error = None
        illuminated_section_mask = None

        self.show_status(Messages.calibrating_colon + Messages.solid_bright_and_dark_field)
        
        self.calibrator.take_solid_bright_and_dark_field_data()
        solid_bright_pics, solid_dark_pics = self.calibrator.get_solid_bright_and_dark_cam_pics()
        
        self.calibrator.calculate_bright_and_dark_levels()
        bright_level, dark_level = self.calibrator.get_bright_and_dark_levels()
        
        self.show_status(Messages.done_calibrating_brightness)
        
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
            beginCoordCalibrationButton = QPushButton(Messages.button_label_begin_coord_calibration)
            beginCoordCalibrationButton.clicked.connect(self.beginCoordCalibrationButtonClicked)

            self.vlayout.addWidget(beginCoordCalibrationButton)
    
    def beginCoordCalibrationButtonClicked(self):
        dlg = CoordCalibrationDialog(self.pycroInterface, self.raspiInterface, self.calibrator, self.exposureMs)
        dlg.exec()


class DmdCalibrationDialog(QDialog):
    def __init__(self, pycroInterface, raspiInterface):
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
        self.beginButton.clicked.connect(self.brightness_calibration_button_clicked)

        self.vlayout.addWidget(self.beginButton)
        

        self.setLayout(self.vlayout)
        
        self.pycroInterface = pycroInterface
        self.raspiInterface = raspiInterface
        # self.usingStandins = usingStandins
        self.calibrator = Calibrator(self.pycroInterface, self.raspiInterface, self.exposureMs)


    def brightness_calibration_button_clicked(self):
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
        
        dlg = BrightnessCalibrationDialog(self.pycroInterface, self.raspiInterface, self.calibrator, exposureFlt)
        dlg.exec()
