=========================
Installation Instructions
=========================

These are instructions for installation of the server and the clients respectively.


Server
======

From the server side, PyExpLabSys is basically only dependent on a functional MariaDB
installation prepared with the needed structure.

TODO: Describe the DB-structure and provide templates for the needed tables.

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


Installing without bootstrap
----------------------------

In the case that you want to install `PyExpLabSys` on a non-dedicated client, you would
most likely want to skip the bootstrap-script. In that case you can get a functional
minimal installati9on by simply performing the local pip-install into a local venv and
copy `PyExpLabSys/bootstrap/user_settings.yaml` to `~/.config/PyExpLabSys/` and modify
to your local setup.
