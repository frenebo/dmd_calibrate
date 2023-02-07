import argparse
from scripts.desktop.calibrate import calibrate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Program for communicating with raspberry Pi over network (local network or internet)"
        "by running the matching interactive script on the Pi through ssh and sending and receiving files through ssh.")
    parser.add_argument('hostname', help="hostname to find raspberry pi, for example 'raspberrypi' is the default for a raspi on a local network")
    parser.add_argument('username', help="Username to login on raspberry pi")
    parser.add_argument('password', help="Password to login on raspberry pi")
    parser.add_argument('--workdir', default='dmdworkdir', help="Directory for placing temporary files sent to and from raspi")


    args = parser.parse_args()

    calibrate(
        args.hostname,
        args.username,
        args.password,
        args.workdir)