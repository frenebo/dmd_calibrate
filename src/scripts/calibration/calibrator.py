import numpy as np
import cv2

from ..constants import DmdConstants

class CalibrationException(Exception):
    pass


class Calibrator:
    def __init__(self, pycroInterface, raspiInterface, cameraExposureMs, usingStandins=False):
        self.pycroInterface = pycroInterface
        self.raspiInterface = raspiInterface
        self.cameraExposureMs = cameraExposureMs
        self.usingStandins = usingStandins
        
        self.dmd_dims = ( DmdConstants.DMD_H, DmdConstants.DMD_W )
        
        self.number_of_solid_field_calibration_exposures = 10
        self.solid_field_calculation_gaussian_blur_sigma = 201

        self.max_relative_variance_rel_to_b_w_diff = 0.1
        
        self._solid_bright_field_cam_pics = None
        self._solid_dark_field_cam_pics = None
        self._dark_level = None
        self._bright_level = None
    
    def turn_on_laser_and_setup_pycromanager(self):
        self.pycroInterface.set_imaging_settings_for_acquisition(
            multishutterPreset="NoMembers",
            sapphireOnOverride="on",
            exposureMs=self.cameraExposureMs,
            sapphireSetpoint="110",
            )    
    
    def calibrate_solid_bright_and_dark_field(self):
        try:
            self.turn_on_laser_and_setup_pycromanager()

            with self.raspiInterface.image_sender() as raspiImageSender:
                print(raspiImageSender)
                solid_bright_field_dmd_pattern = np.ones(self.dmd_dims, dtype=float)
                raspiImageSender.send_image(solid_bright_field_dmd_pattern)
                
                if self.usingStandins:
                    self.pycroInterface.standin_pretend_solid_white()

                snapped_bright_pics = []
                for i in range(self.number_of_solid_field_calibration_exposures):
                    cam_pic = self.pycroInterface.snap_pic()
                    snapped_bright_pics.append(cam_pic)
                
                
                solid_dark_field_dmd_pattern = np.zeros(self.dmd_dims, dtype=float)
                raspiImageSender.send_image(solid_dark_field_dmd_pattern)
                
                if self.usingStandins:
                    self.pycroInterface.standin_pretend_solid_black()

                snapped_dark_pics = []
                for i in range(self.number_of_solid_field_calibration_exposures):
                    cam_pic = self.pycroInterface.snap_pic()
                    snapped_dark_pics.append(cam_pic)
            
            self._solid_bright_field_cam_pics = snapped_bright_pics
            self._solid_dark_field_cam_pics = snapped_dark_pics
        except Exception as e:
            raise CalibrationException(str(e))
        finally:
            self.turn_off_laser_and_turn_off_shutter()

    
    def get_solid_bright_and_dark_cam_pics(self):
        return self._solid_bright_field_cam_pics, self._solid_dark_field_cam_pics
    
    def get_bright_and_dark_levels(self):
        return self._bright_level, self._dark_level
    
    def get_illuminated_section_mask(self):
        return self._illuminated_section_mask

    
    def calculate_bright_and_dark_levels(self):
        if self._solid_dark_field_cam_pics == None or self._solid_bright_field_cam_pics == None:
            raise CalibrationException("Cannot calculate bright and dark levels until solid dark field and solid bright field calibration images have been exposed")
        
        if (
            len(self._solid_bright_field_cam_pics) != self.number_of_solid_field_calibration_exposures or
            len(self._solid_dark_field_cam_pics) != self.number_of_solid_field_calibration_exposures
            ):
            raise CalibrationException("Number of bright and dark solid field calibration pics " +
                "should both be {}, instead # of bright is {} and # of dark is {}".format(
                    self.number_of_solid_field_calibration_exposures,
                    len(self._solid_bright_field_cam_pics),
                    len(self._solid_dark_field_cam_pics),
                ))

        all_dark_samples = np.array(self._solid_dark_field_cam_pics)
        all_bright_samples = np.array(self._solid_bright_field_cam_pics)

        var_within_dark = np.average(np.var(all_dark_samples, axis=0))
        var_within_bright = np.average(np.var(all_bright_samples, axis=0))


        avg_dark = np.average(all_dark_samples, axis=0)
        avg_bright = np.average(all_bright_samples, axis=0)


        var_between_avg_dark_and_bright = np.average(np.var(np.array([avg_dark, avg_bright]), axis=0))

        # If the dmd lit-up area only covers part of the image, we need to find the bright level based on the area that is bright.
        # averaged_dark_img_field = np.mean(all_dark_samples)
        # averaged_bright_img_field = np.mean(all_bright_samples)
        mean_dark_brightness = np.average(avg_dark)
        mean_bright_brightness = np.average(avg_bright)
        
        gaussian_blur_xy = (self.solid_field_calculation_gaussian_blur_sigma, self.solid_field_calculation_gaussian_blur_sigma)
        blurred_dark_avg = cv2.GaussianBlur(avg_dark, gaussian_blur_xy, 0)
        blurred_bright_avg = cv2.GaussianBlur(avg_bright, gaussian_blur_xy, 0)

        # The pixels that are on average more bright in bright than dark images give us the mask for the part of the image
        # We use to find the bright level. We use the blurred images to find this region so that speckles don't affect it too much
        illuminated_section_mask = blurred_bright_avg > mean_dark_brightness + (mean_bright_brightness - mean_dark_brightness) * 0.3

        
        # show_dark_bright_calibration_images(bright_photos, dark_photos, bright_level, dark_level)
        
        # Check that there is a statistical difference between datasets -
        # This should show whether there is a detected difference between
        # DMD "bright screen" and "dark screen"
        if (
            (var_within_dark > self.max_relative_variance_rel_to_b_w_diff * var_between_avg_dark_and_bright) or
            (var_within_bright > self.max_relative_variance_rel_to_b_w_diff * var_between_avg_dark_and_bright)
            ):
            raise CalibrationException(
                "Variance among calibration images is high compared to variance " +
                "between average dark image and average bright image. \n" +
                "Var within dark calibration images: {} within bright calibration images: {}. \nVar between average dark and average bright image: {}.".format(
                    var_within_dark,
                    var_within_bright,
                    var_between_avg_dark_and_bright,
                ) +
                "Are the DMD and laser on? \nWhen displaying a bright image, is the projected image overlapping the area captured by the camera sensor? \nIs the exposure time long enough?"
            )
        self._dark_level = mean_dark_brightness
        self._bright_level = np.average(avg_bright[illuminated_section_mask])
        self._illuminated_section_mask = illuminated_section_mask

    
    def calibrate_coords(self):
        if self._bright_level is None or self._dark_level is None:
            raise CalibrationException("Must calibrate bright and dark levels before calibrating coordinates")
        
        # circle_diameter = 51
        # edge_margin = math.ceil(circle_diameter / 2)
        
        # gridXPositions = np.arange(edge_margin, DmdConstants.DMD_W - 1 - edge_margin, 200)
        # gridYPositions = np.arange(edge_margin, DmdConstants.DMD_H - 1 - edge_margin, 200)

        # for x_pos in gridXPositions:
        #     for y_pos in gridYPositions:
        #         self.show_status(Messages.displaying_calibration_circle_at_dmd_coords + " {}, {}".format(
        #             x_pos,
        #             y_pos
        #         ))
        #         marker_img_dmd = np.zeros( (DmdConstants.DMD_H, DmdConstants.DMD_W), dtype=float)

        #         draw_white_circle(marker_img_dmd, circle_diameter, x_pos, y_pos)
        #         # circle_

        #         # print("Showing calibration circle at x {}, y {} on dmd".format(circle_dmd_x, circle_dmd_y))
        #         # marker_img_dmd = np.zeros( (DMD_H, DMD_W), dtype=float)



    
    def turn_off_laser_and_turn_off_shutter(self):
        self.pycroInterface.set_imaging_settings_for_acquisition(
            multishutterPreset="NoMembers",
            sapphireOnOverride="off",
            )
