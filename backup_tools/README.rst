This folder contains tools to backup and restore a running PyExpLabSys installation.

The backup-tool will iterate through all tables in the database. In accordance to
the conventions of PyExpLabSys, the backup script is aware of the difference between
dateplots and measurements.

For dateplots, every table is simply dump individually. For measurements, the script
will groups `measurements` and `xy`-tables int a single dump-file.

If any tables are left after the export of dateplots measurements and measurements will
be combined into a `misc`-dump, this will contain items such as `dateplots_descriptions`,
`alarms` and some of the service tables.
