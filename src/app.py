import sys
from PyQt6.QtWidgets import QApplication

from scripts.mainwindow import MainWindow


if __name__ == "__main__":
    app = QApplication([])
    print(sys.argv)
    if len(sys.argv) >= 2 and sys.argv[1] == "standins":
        useStandIns = True
    else:
        useStandIns = False

    window = MainWindow(useStandIns=useStandIns)
    window.show()

    app.exec()