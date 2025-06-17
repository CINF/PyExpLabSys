This is a collection of standard loggers to avoid repeating usefull code in machines.

All loggers in the directory will look for TOML based configuration in
~/machines/HOSTNAME/config.toml and credentials in ~/machines/HOSTNAME/credentials.toml

So far the available loggers are

 * ADS Analog logger


A number of existing loggers currently use various other configurations and will soon (tm)
move to this folder and follow the same configuration convention:

 * edwards_nxds_logger
 * turbo_logger
 * wind_speed_logger


Analog logger
=============

Use up to two ADS1115-based anlog input units to record up to eight analog signals.
The ADS driver itself is not included in PyExpLabSys since a good driver already
exists pip: https://pypi.org/project/ADS1x15-ADC/ - install with `pip install ads1x115`


