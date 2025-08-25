This folder contains tools to backup and restore a running PyExpLabSys installation.

The backup-tool will iterate through all tables in the database. In accordance to
the conventions of PyExpLabSys, the backup script is aware of the difference between
dateplots and measurements.

For dateplots, every table is simply dump individually. For measurements, the script
will groups `measurements` and `xy`-tables int a single dump-file.

If any tables are left after the export of dateplots measurements and measurements will
be combined into a `misc`-dump, this will contain items such as `dateplots_descriptions`,
`alarms` and some of the service tables.

backup
------
Currently, the credentials for the sql-server is hard-codet in the top of the script -
this will change soon, but for now the only external configuration is the path to
the backup-folder. This can be given in two ways; either via the env-variable
`PYEXPLABSYS_EXPORT` or via the commandline option `--path`

One way to use the env-variable approach is to use the BASH to set the variable:
`export PYEXPLABSYS_EXPORT='/home/roje/Backups/nanomadedata'/`

To run the actual backup, execute the script (including the `--path` parameter if the
env-variable is not set):
 `python PyExpLabSys/backup_tools/sql_backup.py`

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
