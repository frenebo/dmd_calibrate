# dmd_calibrate

Run src/app.py from the command line to start the DMD calibration app. Use it with the --help flag to see the options for running it:
```console
$ python3 src/app.py --help
```

The DMD calibration code is separate from the code for the app, and can be found in src/scripts/calibration. The code used to interface with microscope hardware through Micromanager 2.0's Pycromanager API is in src/scripts/deviceinterfaces/pycrointerface.py. The code for interfacing with the Raspberry Pi over SSH is in src/scripts/deviceinterfaces/raspiinterface.py.
