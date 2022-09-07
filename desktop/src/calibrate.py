
import numpy as np
import tifffile
import pycromanager
import math
import os

from .raspiinterface import RaspiController
from .camera import take_micromanager_pic

DMD_H_W = (800, 1280)

def save_img_for_dmd(np_float_img, path):
    assert np_float_img.dtype == float, "Image should be float array"
    assert np.all(np_float_img >= 0), "Image should have no negative brightness values"
    assert np.all(np_float_img <= 1), "Image should have no brightness values greater than 1"
    assert np_float_img.shape == DMD_H_W, "Numpy float image should have shape {}".format(DMD_H_W)

    max_int16 =  np.iinfo(np.uint16).max

    np_int8_img = (np_float_img *  max_int16 ).astype(np.uint16)


    tifffile.imwrite(path, np_int8_img)

def calibrate(core, raspi_controller, workdir):
    dmd_img_dir = os.path.join(workdir, "imgsfordmd")
    os.makedirs(dmd_img_dir, exist_ok=True)

    black_img_dmd = np.zeros(DMD_H_W, dtype=float)
    black_img_dmd_path = os.path.join(dmd_img_dir, "allblack.tiff")
    save_img_for_dmd(black_img_dmd, black_img_dmd_path)
    raspi_controller.send_and_show_image_on_dmd(black_img_dmd_path)

    black_img_microphoto = take_micromanager_pic(core)

    white_img_dmd = np.ones(DMD_H_W, dtype=float)
    white_img_dmd_path = os.path.join(dmd_img_dir, "allwhite.tiff")
    save_img_for_dmd(white_img_dmd, white_img_dmd_path)
    raspi_controller.send_and_show_image_on_dmd(white_img_dmd_path)

    white_img_microphoto = take_micromanager_pic(core)

    dmd_h, dmd_w = DMD_H_W

    # edge_margin = 10
    circle_diameter = 19
    edge_margin = math.ceil(circle_diameter / 2)
    
    grid_x_positions = np.arange(edge_margin, dmd_w - 1 - edge_margin)
    grid_y_positions = np.arange(edge_margin, dmd_h - 1 - edge_margin)

    for dmd_center_y in grid_y_positions:
        for dmd_center_x in grid_x_positions:
            marker_img_dmd = np.zeros(DMD_H_W, dtype=float)
            


    # raspi_controller.send_and_show_image_on_dmd
    # @TODO : ignore points that are less than half a radius from an edge of the camera field
    pass

def calibrate(hostname, username, password, pi_interactive_script_path, workdir):
    os.makedirs(workdir, exist_ok=True)


    with pycromanager.Bridge() as bridge:
        core = bridge.get_core()
        raspi_controller = RaspiController(hostname, username, password, pi_interactive_script_path)

        calibrate(core, raspi_controller, workdir)

