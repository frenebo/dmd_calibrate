import sys
import argparse
import os
from PyQt6.QtWidgets import QApplication

from scripts.mainwindow import MainWindow


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="DMD Microscope Utility")
    parser.add_argument(
        "--standins",
        default=False,
        action="store_true",
        help="Use pretend devices instead of hardware, for testing")
    parser.add_argument("--tempdir", default="dmdworkdir", type=str, help="Directory to place temporary files while running")

    args = parser.parse_args()

    if not os.path.exists(args.tempdir):
        raise Exception("Cannot find working dir '{}' - create it to continue".format(args.tempdir))
    
    # print("using standins?:")
    # if args.standins:
    #     print("Using standins")

    app = QApplication([])
    
    window = MainWindow(args.tempdir, useStandIns=args.standins)
    window.show()

    app.exec()