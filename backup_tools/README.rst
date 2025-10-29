This folder contains tools to backup and restore a running PyExpLabSys installation.

The backup-tool will iterate through all tables in the database. In accordance to
the conventions of PyExpLabSys, the backup script is aware of the difference between
dateplots and measurements.

For dateplots, every table is simply dumped individually. For measurements, the script
will group `measurements` and `xy`-tables into a single dump-file.

If any tables are left after the export of dateplots and measurements they will
be combined into a `misc`-dump, this will contain items such as `dateplots_descriptions`,
`alarms` and some of the service tables.

Server requirements
-------------------

Besides a functional `PyExpLabSys`-installation, the server will need to have the
mariadb command-line tools and the `gunzip` command installed.

backup
------
The credentials for the sql-server is given to the script via environment variables.
This makes it relatively easy to keep the credentaials away from the code without
exposing them to the command line. The variables can be set in any way the sysadmin
prefers, but a convential way to it is via a files named `.env` that can be sourced
from the shell right before the execution of the scripts. The content of the file
should be something like this::

 export PYEXPLABSYS_HOST='<HOST>'
 export PYEXPLABSYS_USER='<USER>'
 export PYEXPLABSYS_PASSWD='<PASSWD>'
 export PYEXPLABSYS_DB='<DB>'
 export PYEXPLABSYS_EXPORT_PATH='<PATH>'

 export PYEXPLABSYS_RESTORE_HOST='<RESTORE_HOST>'
 export PYEXPLABSYS_RESTORE_USER='<RESTORE_USER>'
 export PYEXPLABSYS_RESTORE_PASSWD='<RESTORE_PASSWD>'
 export PYEXPLABSYS_RESTORE_DB='<RESTORE_DB>'

To populate the environment, simply run::
 source .venv

The restore-credentails can of course be the same as the main credentials if the
purpose is to restore a broken install, but will typically be a different server
to serve the day-to-day purpose of keeping a semi up-to-date backup server.

If the script needs to be run in a one-shot mode with export to a different path,
the path can be overruled via the commandline option `--path`

To run the actual backup, execute the script::
 python PyExpLabSys/backup_tools/sql_backup.py`

As part of the backup, a table named `metadata.sql` will be created. This table contains
information about all database users, and create statements for the table-structure.

FUTURE: Differential backups


Restore
-------

Write about how to prepare the database for the import.



System maintainence
-------------------

It is adviced to run the backup tool regularly....

Consider to set up restore as part of the daily procedure.
