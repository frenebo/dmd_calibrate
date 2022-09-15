
import numpy as np
import tifffile
import pycromanager
import math
import os
import cv2

from .raspiinterface import RaspiController
from .camera import take_micromanager_pic_as_float_arr
from .coordtransformations import best_fit_affine_transform

from ..constants import DMD_W,  DMD_H

# When calibration doesn't work right
class CalibrationException(Exception):
    pass


def save_img_for_dmd(np_float_img, path):
    assert np_float_img.dtype == float, "Image should be float array"
    assert np.all(np_float_img >= 0), "Image should have no negative brightness values"
    assert np.all(np_float_img <= 1), "Image should have no brightness values greater than 1"
    assert np_float_img.shape == (DMD_H, DMD_W), "Numpy float image should have shape {}".format((DMD_H, DMD_W))

    max_int16 =  np.iinfo(np.uint16).max

    np_int8_img = (np_float_img *  max_int16 ).astype(np.uint16)


    tifffile.imwrite(path, np_int8_img)


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
    circ_mask *= 1.0

    # Add white circle to brightness values
    np_float_img[center_x - rad:center_x + rad + 1, center_y - rad:center_y + rad + 1] += circ_mask

    # If the spot wasn't already white, then it'll have brightness more than 1.0 now - fix this here
    np_float_img[np_float_img > 1.0] = 1.0


def get_background_black_and_white_levels(core, raspi_controller, dmd_img_dir):
    # @TODO calibrate these values
    black_samples = 10
    white_samples = 10

    max_relative_variance_rel_to_b_w_diff = 0.1
    max_black_field_var_rel_to_b_w_diff = 0.1
    max_white_field_var_rel_to_b_w_diff = 0.1

    dmd_dims = (DMD_H, DMD_W)

    black_img_dmd = np.zeros( dmd_dims, dtype=float)
    black_img_dmd_path = os.path.join(dmd_img_dir, "allblack.tiff")
    save_img_for_dmd(black_img_dmd, black_img_dmd_path)
    raspi_controller.send_and_show_image_on_dmd(black_img_dmd_path)

    black_photos = []

    for i in range(black_samples):
        black_img_microphoto = take_micromanager_pic_as_float_arr(core)
        black_photos.append(black_img_microphoto)


    white_img_dmd = np.ones(dmd_dims, dtype=float)
    white_img_dmd_path = os.path.join(dmd_img_dir, "allwhite.tiff")
    save_img_for_dmd(white_img_dmd, white_img_dmd_path)
    raspi_controller.send_and_show_image_on_dmd(white_img_dmd_path)

    white_photos = []
    for i in range(white_samples):
        white_img_microphoto = take_micromanager_pic_as_float_arr(core)
        white_photos.append(white_img_microphoto)

    all_black_samples = np.array(black_photos)
    all_white_samples = np.array(white_samples)

    var_within_black = np.average(np.var(all_black_samples, axis=0))
    var_within_white = np.average(np.var(all_white_samples, axis=0))


    avg_black = np.average(all_black_samples, axis=0)
    avg_white = np.average(all_white_samples, axis=0)

    var_between_avg_black_and_white = np.average(np.var(np.array([avg_black, avg_white]), axis=0))

    # Check that there is a significant difference bet
    too_much_black_var = False
    too_much_white_var = False

    if (
        (var_within_black > max_relative_variance_rel_to_b_w_diff * var_between_avg_black_and_white) or
        (var_within_white > max_relative_variance_rel_to_b_w_diff * var_between_avg_black_and_white)
        ):
        raise CalibrationException("Variance among calibration images is high compared to variance between average black image and average white image. Var within black calibration images: {} within white calibration images: {}. Var between average black and average white image: {}. Is the DMD on? When displaying a white image, is the projected image overlapping the area captured by the camera sensor? Is the exposure time long enough?".format(
            var_within_black,
            var_within_white,
            var_between_avg_black_and_white,
        ))

    # In addition to checking the variance of black images relative to each other, make sure the average black image is more or less even.
    var_in_avg_black_img = np.var(avg_black)
    if var_in_avg_black_img > max_black_field_var_rel_to_b_w_diff * var_between_avg_black_and_white:
        raise CalibrationException("The unevenness of the average black field is too high: variance within avg black calibration image is {}, compared to variance between average black and average white image: {}.".format(
            var_in_avg_black_img,
            var_between_avg_black_and_white,
        ))

    var_in_avg_white_img = np.var(avg_white)
    if var_in_avg_white_img > max_white_field_var_rel_to_b_w_diff * var_between_avg_black_and_white:
        raise CalibrationException("The unevenness of the average white field is too high: variance within avg white calibration image is {}, compared to variance between average black and average white image: {}.".format(
            var_in_avg_white_img,
            var_between_avg_black_and_white,
        ))


    # Just call the average pixel value in black images the black level
    black_level = np.average(avg_black)
    # And average pixel value in white images the white level
    white_level = np.average(avg_white)

    return black_level, white_level


def find_blobs_in_photo(np_float_img, black_level, white_level):
    gaussian_blur_sigma = 7
    touching_edge_pixels_threshold = 3

    # Areas closer to white than to black are considered white
    thresh = (black_level + white_level) / 2

    blurred = cv2.GaussianBlur(img, (gaussian_blur_sigma, gaussian_blur_sigma), 0)

    above_thresh = np.uint8(blurred > thresh)

    contours, hierarchy = cv2.findContours(above_thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    found_blobs = []


    for contour_i in range(len(contours)):
        contour = contours[contour_i]
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour,True)


        circularity = 2*np.sqrt(np.pi*area)  / perimeter

        x_min,y_min,width,height = cv2.boundingRect(cntr)

        is_touching_edge = (
            (x_min <= touching_edge_pixels_threshold) or
            (y_min <= touching_edge_pixels_threshold) or
            (x_min + width >= np_float_img.shape[0] - touching_edge_pixels_threshold) or
            (y_min + height >= np.float_img.shape[1] - touching_edge_pixels_threshold)
            )

        M = cv2.moments(big_contour)
        cx = m["m10"]/M["m00"]
        cy = M["m01"]/M["m00"]


        found_blobs.append({
            "touching_edge": is_touching_edge,
            "circularity": circularity,
            "perimeter": perimeter,
            "area": area,
            "centroid_x": cx,
            "centroid_y": cy,
            "x_min": x_min,
            "y_min": y_min,
            "width": width,
            "height": height,
        })

    return found_blobs

def analyze_calibration_measurements(calibration_measurements):
    categorized_measurements = {
        "one_middle_blob": [],
        "middle_blobs_and_boundary_blobs": [],
        "only_boundary_blobs": [],
        "no_blobs": [],
    }

    for datapt in calibration_measurements:
        dmd_circle_x = datapt["dmd_circle_x"]
        dmd_circle_y = datapt["dmd_circle_y"]
        all_detected_blobs = datapt["camera_detected_blobs"]

        middle_blobs = []
        touching_edge_blobs =  []
        for blob in all_detected_blobs:
            if blob["touching_edge"]:
                touching_edge_blobs.append(blob)
            else:
                middle_blobs.append(blob)

        if len(all_detected_blobs) == 0:
            categorized_measurements["no_blobs"].append(datapt)
        else:
            if len(middle_blobs) == 0:
                categorized_measurements["only_boundary_blobs"].append(datapt)
            elif len(edge_blobs) == 0:
                if len(middle_blobs) > 1:
                    raise CalibrationException("Detected multiple possible circles when displaying a circle at DMD coordinates x={} y={}".format(dmd_circle_x, dmd_circle_y))
                categorized_measurements["one_middle_blob"].append(datapt)
            else:
                categorized_measurements["middle_blobs_and_boundary_blobs"].append(datapt)

    dmd_circle_coords = []
    cam_circle_coords = []

    if len(categorized_measurements["one_middle_blob"]) < min_good_points:
        raise CalibrationException("Couldn't get enough circle measurements that were fully in camera field. Needed {}, got {}".format(
            min_good_points,
            len(categorized_measurements["one_middle_blob"])
        ))

    for datapt in categorized_measurements["one_middle_blob"]:
        dmd_circle_x = datapt["dmd_circle_x"]
        dmd_circle_y = datapt["dmd_circle_y"]
        blob = datapt["camera_detected_blobs"][0]

        cam_circle_x = blob["centroid_x"]
        cam_circle_y = blob["centroid_y"]

    found_blobs = []

    for label in range(numLabels):
        # If this blob corresponds to a dark region
        if np.any((labels == 0) == np.logical_not(above_thresh)):
            continue
        # If this blob corresponds to a bright region, then continue to
        x_min, y_min, width, height, area = stats[label]
        centroid_x, centroid_y = centroids[label]

    rms = np.sqrt(np.average(np.square(pred_errors)))
    max_err = np.max(pred_errors)

    return A, b, rms, max_err



def calibrate_geometry(core, raspi_controller, workdir):
    dmd_img_dir = os.path.join(workdir, "imgsfordmd")
    os.makedirs(dmd_img_dir, exist_ok=True)

    black_level, white_level = get_background_black_and_white_levels(core, raspi_controller, dmd_img_dir)

    # dmd_h, dmd_w = DMD_H_W

    fit_transform_max_acceptable_camera_err = 10

    circle_diameter = 19
    edge_margin = math.ceil(circle_diameter / 2)

    grid_x_positions = np.arange(edge_margin, DMD_W - 1 - edge_margin, 70)
    grid_y_positions = np.arange(edge_margin, DMD_H - 1 - edge_margin, 70)

    calibration_measurements = []

    for circle_dmd_y in grid_y_positions:
        for circle_dmd_x in grid_x_positions:
            marker_img_dmd = np.zeros( (DMD_H, DMD_W), dtype=float)

            draw_white_circle(marker_img_dmd, circle_diameter, circle_dmd_x, circle_dmd_y)

            circle_path = os.path.join(dmd_img_dir, "circle_calibration_marker.tiff")
            save_img_for_dmd(marker_img_dmd, circle_path)
            raspi_controller.send_and_show_image_on_dmd(circle_path)

            circle_microphoto = take_micromanager_pic_as_float_arr(core)

            found_cam_circles = find_circles_in_photo(circle_microphoto, black_level, white_level)

            found_blobs = find_blobs_in_photo(circle_microphoto, black_level, white_level)

            calibration_measurements.push({
                "dmd_circle_x": circle_dmd_x,
                'dmd_circle_y': circle_dmd_y,
                "camera_detected_blobs": found_blobs,
            })

    transformA, transformb, fitRms, fitMaxErr = analyze_calibration_measurements(calibration_measurements)

    if fitMaxErr > fit_transform_max_acceptable_camera_err:
        raise CalibrationException("The best fit transformation for dmd and camera coordinates predicts incorrect camera coordinates by {}, more than the max acceptable value of {}".format(
            fitMaxErr,
            fit_transform_max_acceptable_camera_err
        ))


    dmdToCam2x3 = np.zeros((2,3))
    dmdToCam2x3[0:2,0:2] = transformA
    dmdToCam2x3[0:2,2:3] = transformb


    # dmdToCam3x3 = np.zeros((3,3))
    # dmdToCam3x3[0:2,0:2] = transformA
    # dmdToCam3x3[0:2,2:3] = transformb
    # dmdToCam3x3[2,2] = 1.0

    # camToDmd3x3 = np.linalg.inv(dmdToCam3x3)




    # @TODO account for feh latency?

    # raspi_controller.send_and_show_image_on_dmd
    # @TODO : ignore points that are less than half a radius from an edge of the camera field
    # @TODO test with  not enough points

    pass

def calibrate(
    hostname,
    username,
    password,
    pi_interactive_script_path,
    workdir):
    os.makedirs(workdir, exist_ok=True)


    with pycromanager.Bridge() as bridge:
        core = bridge.get_core()
        raspi_controller = RaspiController(hostname, username, password, pi_interactive_script_path)

        try:
            calibrate_geometry(core, raspi_controller, workdir)
        except:
            raspi_controller.stop_showing_image_on_dmd()
            raise
        raspi_controller.stop_showing_image_on_dmd()

