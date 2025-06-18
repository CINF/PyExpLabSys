Overview
========
This is a collection of standard loggers to avoid repeating usefull code in machines.

All loggers in the directory will look for TOML based configuration in
~/machines/HOSTNAME/config.toml and credentials in ~/machines/HOSTNAME/credentials.toml

The content of the configuration file will be dependent on the specific logger. The
credentials file will always have exactly two keys, `user` and `passwd`.


Summary of loggers
==================

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

Configuration
+++++++++++++

Configuration of the logger comes in a number of sections:

 * A single key named `description`: This holds a small description of the system
 * A section named `database`: This holds the information needed to store data - since most
   of this is global to `PyExpLabSys` only a single key is currently in use; `table` which
   holds the name of the dateplot table to store data to.
 * A section named `ADC mapping`: Hold a key for each measurement, using the syntax:
   `i2c_addr.codename` = [adc_channel, offset, scale, min_log_value]
 * An optional section named `RTDs`: I

An example of a configuration file is available at:
https://github.com/nanomade/machines/blob/main/moorfield-cooling-water-raspi01/config.toml

