import numpy as np

from ..constants import DmdConstants

class CalibrationException(Exception):
    pass

class Calibrator:
    def __init__(self, pycroInterface, raspiImageSender, camera_exposure_ms):
        self.pycroInterface = pycroInterface
        self.raspiImageSender = raspiImageSender
        # self.laser_power = laser_power
        self.camera_exposure_ms = camera_exposure_ms
        
        self.dmd_dims = ( DmdConstants.DMD_H, DmdConstants.DMD_W )
        
        self.number_of_solid_field_calibration_exposures = 10
        self.solid_field_calculation_gaussian_blur_sigma = 201

        max_relative_variance_rel_to_b_w_diff = 0.1
        max_dark_field_var_rel_to_b_w_diff = 0.1
        max_bright_field_var_rel_to_b_w_diff = 0.1
        
        self.pycromanager_ready = False
        self.solid_bright_field_cam_pics = None
        self.solid_dark_field_cam_pics = None
    
    def turn_on_laser_and_setup_pycromanager(self):
        self.pycroInterface.set_imaging_settings_for_acquisition(
            multishutter_preset="NoMembers",
            sapphire_on_override="on",
            exposure_ms=self.camera_exposure_ms,
            sapphire_setpoint="110",
            )
        
        self.pycromanager_ready = True
    
    def calibrate_solid_bright_field(self):
        if not self.pycromanager_ready:
            raise CalibrationException("Cannot calibrate bright solid field before pycromanager has been setup through Calibrator")
        
        
        solid_bright_field_dmd_pattern = np.ones(self.dmd_dims, dtype=float)
        self.raspiImageSender.send_image(solid_bright_field_dmd_pattern)
        
        snapped_bright_pics = []
        for i in range(self.number_of_solid_field_calibration_exposures):
            cam_pic = self.pycroInterface.snap_pic()
            snapped_bright_pics.append(cam_pic)
        
        self.solid_bright_field_cam_pics = snapped_bright_pics
        return snapped_bright_pics
    
    def calibrate_solid_dark_field(self):
        if not self.pycromanager_ready:
            raise CalibrationException("Cannot calibrate dark solid field before pycromanager has been setup through Calibrator")
        
        solid_dark_field_dmd_pattern = np.zeros(self.dmd_dims, dtype=float)
        self.raspiImageSender.send_image(solid_dark_field_dmd_pattern)
        
        snapped_dark_pics = []
        for i in range(self.number_of_solid_field_calibration_exposures):
            cam_pic = self.pycroInterface.snap_pic()
            snapped_dark_pics.append(cam_pic)
        
        self.solid_dark_field_cam_pics = snapped_dark_pics
        return snapped_dark_pics
    
    def calculate_bright_and_dark_levels(self):
        if self.solid_dark_field_cam_pics == None or self.solid_bright_field_cam_pics == None:
            raise CalibrationException("Cannot calculate bright and dark levels until solid dark field and solid bright field calibration images have been exposed")
        
        if (
            len(self.solid_bright_field_cam_pics) != self.number_of_solid_field_calibration_exposures or
            len(self.solid_dark_field_cam_pics) != self.number_of_solid_field_calibration_exposures
            ):
            raise CalibrationException("Number of bright and dark solid field calibration pics " +
                "should both be {}, instead # of bright is {} and # of dark is {}".format(
                    self.number_of_solid_field_calibration_exposures,
                    len(self.solid_bright_field_cam_pics),
                    len(self.solid_dark_field_cam_pics),
                ))
        


        all_dark_samples = np.array(self.solid_dark_field_cam_pics)
        all_bright_samples = np.array(self.solid_bright_field_cam_pics)

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
        print("mean dark: ", mean_dark_brightness)
        # print("mean bright: ", mean_bright_brightness)

        dark_level = mean_dark_brightness
        bright_level = np.average(avg_bright[illuminated_section_mask])


        print("bright level: ", bright_level)
        
        raise NotImplementedError()
        show_dark_bright_calibration_images(bright_photos, dark_photos, bright_level, dark_level)
        
        # Check that there is a statistical difference between datasets -
        # This should show whether there is a detected difference between
        # DMD "bright screen" and "dark screen"
        if (
            (var_within_dark > max_relative_variance_rel_to_b_w_diff * var_between_avg_dark_and_bright) or
            (var_within_bright > max_relative_variance_rel_to_b_w_diff * var_between_avg_dark_and_bright)
            ):
            raise CalibrationException(
                "Variance among calibration images is high compared to variance " +
                "between average dark image and average bright image. " +
                "Var within dark calibration images: {} within bright calibration images: {}. Var between average dark and average bright image: {}.".format(
                    var_within_dark,
                    var_within_bright,
                    var_between_avg_dark_and_bright,
                ) +
                "Are the DMD and laser on? When displaying a bright image, is the projected image overlapping the area captured by the camera sensor? Is the exposure time long enough?"
            )

        return dark_level, bright_level

            
    
    def turn_off_laser_and_turn_off_shutter(self):
        self.pycroInterface.set_imaging_settings_for_acquisition(
            multishutter_preset="NoMembers",
            sapphire_on_override="off",
            )
