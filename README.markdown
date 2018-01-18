
```
 _____       ______            _           _     _____
|  __ \     |  ____|          | |         | |   / ____|
| |__) |   _| |__  __  ___ __ | |     __ _| |__| (___  _   _ ___
|  ___/ | | |  __| \ \/ / '_ \| |    / _` | '_ \\___ \| | | / __|
| |   | |_| | |____ >  <| |_) | |___| (_| | |_) |___) | |_| \__ \
|_|    \__, |______/_/\_\ .__/|______\__,_|_.__/_____/ \__, |___/
        __/ |           | |                             __/ |
       |___/            |_|                            |___/
```

# Python for Experimental Labs System

[![Documentation Status](https://readthedocs.org/projects/pyexplabsys/badge/?version=latest)](http://pyexplabsys.readthedocs.io/?badge=latest)

## About PyExpLabSys

This project contains various python code useful in experimental labs,
such as equipment drivers, data logging and network data exchange
components.

The project is
[documented](http://pyexplabsys.readthedocs.org/en/latest/) with
[Sphinx](http://sphinx-doc.org/) on the [read the docs
webpage](https://readthedocs.org/), but the documentation is still in
its early stages.

PyExpLabSys is an attempt to share the Python code produced at the
SurfCat section at the Technical University of Denmark (DTU). As such,
the development is driven by the needs of the department, which means
that different components have different levels of maturity.

## Support

Support is provided by the authors in their spare time, so we cannot
always reply immediately, but we will try to help when we can.

Support is provided via the #PyExpLabSys IRC channel on freenode and
issues on Github.

## Drivers

The project includes project drivers for a number of instruments. Currently all
of the drivers must be configured by manually changing hard-coded values in the
code. The list of instruments with usable (but non-complete drivers), are:

* Agilent 34410A: This driver is currently able to do basic operations such as
  changing measurement type and read values from the instrument. Currently
  only the USB interface is supported (through the USBTMC kernel-driver). The
  driver will most likely also work with the Agilent 34411A and with minor
  modifications possibly also the 34401A (in that case through the serial
  interface).
  
* CPX400DP: This driver is fairly complete with support for setting and reading
  back values from the instrument. Currently only the USB interface is tested,
  but since the USB interface exposes a virtual serial port, most likely the
  serial interface will work with no problems.
  
* Varian XGS600: This driver is not complete but fully functional for reading
  pressures from the gauge controller through the serial port of the device.
  
* nidaq: Not a driver as such (actually all driver functionality comes through
  NI DAQmx and the nidaqmx-python wrapper for this driver), but serves as an
  example implementation of how to read out values from instruments that
  exposes an analog output.
  
## Data logging

The project includes example code showing how to make a continuously running
data-logger. The program will set up a number of threaded classes that will
collect data in the background and log it to a MySQL database if the values
changes more than a given amount or with regular time intervals.

## GUI-elements

The projects includes two different example of gui-development usefull in an
experimental lab. One example show how to make running plot of a measured
value. The other example show a functional gui for the Agilent 34410A driver.
