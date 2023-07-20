import numpy as np
import cv2

from ..constants import DmdConstants
from ..utilities.coordtransformations import best_fit_affine_transform

class CalibrationException(Exception):
    pass


class Calibrator:
    def __init__(self, pycroInterface, raspiInterface, cameraExposureMs, usingStandins=False):
        self.pycroInterface = pycroInterface
        self.raspiInterface = raspiInterface
        self.cameraExposureMs = cameraExposureMs
        self.usingStandins = usingStandins
        
        self.dmd_dims = ( DmdConstants.DMD_H, DmdConstants.DMD_W )
        
        # Brightness calibration configuration
        self.number_of_solid_field_calibration_exposures = 10
        self.solid_field_calculation_gaussian_blur_sigma = 201

        self.max_relative_variance_rel_to_b_w_diff = 0.1
        
        # Brightness calibration results
        self._solid_bright_field_cam_pics = None
        self._solid_dark_field_cam_pics = None
        self._dark_level = None
        self._bright_level = None
        
        # Coordinate calibration configuration
        self.circle_diameter = 31
        self.circle_spacing = 100
        self.circle_identification_gaussian_blur_sigma = 100
        
        # Throw out identified circle candidates that too close enough to edge
        self.min_blob_distance_to_edge = 50
        self.blob_min_circularity = 0.75
        
        # Coordinate calibration results
        self._dmd_coords_and_acquired_images = None
    
    def turn_on_laser_and_setup_pycromanager(self):
        self.pycroInterface.set_imaging_settings_for_acquisition(
            multishutterPreset="NoMembers",
            sapphireOnOverride="on",
            exposureMs=self.cameraExposureMs,
            sapphireSetpoint="110",
            )    
    
    def take_solid_bright_and_dark_field_data(self):
        try:
            self.turn_on_laser_and_setup_pycromanager()

            with self.raspiInterface.image_sender() as raspiImageSender:
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

    def create_calibration_positions(self):
        assert int(self.circle_diameter) == self.circle_diameter, "Circle diameter should be integer number of pixels"
        assert self.circle_diameter % 2 == 1, "Calibration circle diameter should be odd"
        
        # Radius rounded down = circle_diameter // 2
        x_min = self.circle_diameter // 2
        x_max = self.dmd_dims[1] - 1 - self.circle_diameter // 2
        
        y_min = self.circle_diameter // 2
        y_max = self.dmd_dims[0] - 1 - self.circle_diameter // 2
        
        if y_max - y_min < self.circle_spacing or x_max - x_min < self.circle_spacing:
            raise Exception("Provided circle spacing is too large to fit on dmd: diameter = {}, spacing = {}, DMD dimensions = {}".format(
                self.circle_diameter,
                self.circle_spacing,
                self.dmd_dims,
                ))
        
        num_x = (x_max - x_min) // self.circle_spacing
        num_y = (y_max - y_min) // self.circle_spacing
        
        # Round to evenly spaced coordinates to integers
        x_positions = np.rint(np.linspace(x_min, x_max, num_x))
        y_positions = np.rint(np.linspace(y_min, y_max, num_y))
        
        return x_positions, y_positions
    
    def create_circle_pattern_at_position(self, x_pos, y_pos):
        yy,xx = np.meshgrid(np.arange(self.dmd_dims[0]), np.arange(self.dmd_dims[1]))
        
        radius = self.circle_diameter / 2 # float - if diameter = 5, radius = 2.5
        # Mask is true within radius from y_pos, x_pos
        circle_mask = (yy - y_pos) ** 2 + (xx - x_pos) ** 2 <= radius ** 2
        
        pattern = np.zeros(self.dmd_dims, dtype=float)
        pattern[circle_mask] = 1.0
        
        return pattern
    
    def take_coord_calibration_data(self):
        if self._bright_level is None or self._dark_level is None:
            raise CalibrationException("Must calibrate bright and dark levels before calibrating coordinates")
        
        try:
            self.turn_on_laser_and_setup_pycromanager()
            
            with self.raspiInterface.image_sender() as raspiImageSender:
                # Take calibration data
                x_positions, y_positions = self.create_calibration_positions()
                
                data_taken = []
                
                for y_pos in y_positions:
                    for x_pos in x_positions:
                        pattern = self.create_circle_pattern_at_position(x_pos, y_pos)
                        raspiImageSender.send_image(pattern)
                        
                        cam_pic = self.pycroInterface.snap_pic()
                        data_taken.append({
                            "dmd_x_pos": x_pos,
                            "dmd_y_pos": y_pos,
                            "cam_pic": cam_pic,
                        })
                self._dmd_coords_and_acquired_images = data_taken
                
        except Exception as e:
            raise CalibrationException(str(e))
        finally:
            self.turn_off_laser_and_turn_off_shutter()
    
    def find_blobs_in_photo(self, cam_pic):
        # Change coordinate order to match the x,y order used by cv2
        cv2_image = np.swapaxes(cam_pic, 0, 1)
        thresh = (self._bright_level + self._dark_level) / 2
        
        sig = self.circle_identification_gaussian_blur_sigma
        blurred = cv2.GaussianBlur(cv2_image, (sig, sig), 0)
        above_thresh = np.uint8(blurred > thresh)
        
        img_contours, _ = cv2.findContours(above_thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)        
        
        good_blobs = []
        
        for i in range(len(img_contours)):
            contour = img_contours[i]
            
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour,True)

            if perimeter <= 0 or area <= 0:
                continue

            circularity = 2*np.sqrt(np.pi*area) / perimeter
            
            if circularity < self.blob_min_circularity:
                continue

            x_min, y_min, x_width, y_height = cv2.boundingRect(contour)

            is_touching_edge = (
                (x_min <= self.min_blob_distance_to_edge) or
                (y_min <= self.min_blob_distance_to_edge) or
                (x_min + x_width - 1 >= cv2_image.shape[0] - self.min_blob_distance_to_edge) or
                (y_min + y_height - 1 >= cv2_image.shape[1] - self.min_blob_distance_to_edge)
                )
                
            if is_touching_edge:
                continue

            M = cv2.moments(contour)

            cx = M["m10"]/M["m00"]
            cy = M["m01"]/M["m00"]
            
            good_blobs.append({
                "cx": cx,
                "cy": cy,
                "contour": contour,
                "area": area,
            })
        
        return good_blobs
    
    def calculate_coord_calibration(self):
        if self._dmd_coords_and_acquired_images == None:
            raise CalibrationException("Cannot calculate coordinate calibration, have not yet taken coord calibration data.")
        
        if self._dark_level is None or self._bright_level is None:
            raise CalibrationException("Cannot calculate coordinate calibration, bright and dark level has not been calculated yet.")
        
        # data_pts:
        coord_pairs = []
        for data_pt in self._dmd_coords_and_acquired_images:
            dmd_x = data_pt["dmd_x_pos"]
            dmd_y = data_pt["dmd_y_pos"]
            cam_pic = data_pt["cam_pic"]
            
            found_blobs = self.find_blobs_in_photo(cam_pic)
            
            if len(found_blobs) != 0:
                continue
            
            cam_x = found_blobs[0]["cx"]
            cam_y = found_blobs[0]["cy"]
            coord_pairs.append({
                "cam_x": cam_x,
                "cam_y": cam_y,
                "dmd_x": dmd_x,
                "dmd_y": dmd_y,
            })
        
        dmd_coords = [[p["dmd_x"], p["dmd_y"]] for p in coord_pairs]
        cam_coords = [[p["cam_x"], p["cam_y"]] for p in coord_pairs]
        
        # Transform to 2xN arrays
        dmd_coords = np.array(dmd_coords).T
        cam_coords = np.array(cam_coords).T
        
        A, b = best_fit_affine_transform(dmd_coords, cam_coords)
        
        print("A: {}, b: {}".format(A,b))
            
        # blurred = cv2.GaussianBlur()
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
