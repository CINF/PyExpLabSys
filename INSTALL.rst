=========================
Installation Instructions
=========================

These are instructions for installation of the server and the clients respectively.

Notice, that if you are interested in PyExpLabSys only for the collection of drivers
and not so much for the data logging framework, you do NOT need a server. In that
case you can simply follow the minimal install procedure described in
the section `Installing without bootstrap`.

Server
======

From the server side, PyExpLabSys is basically only dependent on a functional MariaDB
installation prepared with the needed structure.

Database structure
------------------

PyExpLabSys use only a single database. This can be named in any wanted way - historicly
most installations has used a form of <localname>data, eg. cinfdata, nanomadedata,
homedata, etc...

Table structure
---------------

In order to allow the PyExpLabSys installation to work seemlessly with a corresponding
`cinfdata` installation, a number of tables should exist. An empty MariaDB dump-file is
provided as a starting point for this, `PyExpLabSys/bootstrap/cinfdata.sql`.
The provided tables include:

 * alarm
 * alarm_log
 * plot_com
 * plot_com_in
 * plot_com_out
 * short_links
 * dateplots_descriptions

Besides these, the actual data is kept in tables with a naming scheme as described in
the main docs. For the install procedure, a few selected tables are provided:

 * dateplots_cryostat
 * measurements_cryostat
 * measurements_dummy
 * xy_values_cryostat
 * xy_values_dummy

If you are using PyExpLabSys only for dateplot-data, you can delete everything
but the dateplot example. If you do not happen have a cryostat, this table can
be renamed and copied to suit your particular needs.



Clients
=======

PyExpLabSys is unfortunately not yet available from pip, but is possible to pip-install
from a local git-checkout, which is the recommended installation method. The following
proceudre assumes installation on a dedicated mini-client (typically a Raspberry Pi),
since the used bootstrap script make quite a mess on a system if it supposed to run
on a system with other tasks besides PyExpLabSys.

 * Clone the PyExpLabSys repo: `git clone https://github.com/cinf/PyExpLabSys`
 * Run the bootstrap script: `./bootstrap/bootstrap_linux.bash all`
 * `sudo reboot`

Bootstrap ensures that the needed apt-packages are available and setup the local
environment with niceness such as support for AUTOSTART and status screen upon login.

 * Now, setup a venv: `python3 -mvenv venv`
 * `source venv/bin/activate`
 * Install PyExpLabSys:
 * `cd PyExpLabSys/`
 * `pip install .`

Now, modify `~/.config/PyExpLabSys/user.settings.yaml` to fit your local setup.

.. _install_without_boostrap:

Installing without bootstrap
----------------------------

In the case that you want to install `PyExpLabSys` on a non-dedicated client, you would
most likely want to skip the bootstrap-script. In that case you can get a functional
minimal installati9on by simply performing the local pip-install into a local venv and
copy `PyExpLabSys/bootstrap/user_settings.yaml` to `~/.config/PyExpLabSys/` and modify
to your local setup.
