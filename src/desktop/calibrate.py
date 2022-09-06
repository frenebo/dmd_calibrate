
import numpy as np
import pycromanager
import argparse

from .raspiinterface import RaspiController
from .camera import read_image

DMD_H_W = (800, 1280)

def save_img_for_dmd(np_float_img, path):
    assert np_float_img.dtype == float, "Image should be float array"
    assert np.all(np_float_img >= 0), "Image should have no negative brightness values"
    assert np.all(np_float_img <= 1), "Image should have no brightness values greater than 1"

    

def calibrate(core, raspi_controller):
    black_img = np.zeros(DMD_H_W, dtype=float)
    # raspi_controller.send_and_show_image_on_dmd
    # @TODO : ignore points that are less than half a radius from an edge of the camera field
    pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Program for communicating with raspberry Pi over network (local network or internet)"
        "by running the matching interactive script on the Pi through ssh and sending and receiving files through ssh.")
    parser.add_argument('hostname', help="hostname to find raspberry pi, for example 'raspberrypi' is the default for a raspi on a local network")
    parser.add_argument('username', help="Username to login on raspberry pi")
    parser.add_argument('password', help="Password to login on raspberry pi")
    parser.add_argument('pi_interactive_script_path', help="Path on Pi for interactive python 3 script, the Pi should have downloaded the matching interactive python script to run and receive instructions")
    parser.add_argument('--workdir', default='dmdworkdir', help="Directory for placing temporary files sent to and from raspi")


    args = parser.parse_args()

    with pycromanager.Bridge() as bridge:
        core = bridge.get_core()
        controller = RaspiController(args.hostname, args.username, args.password, args.pi_interactive_script_path)

