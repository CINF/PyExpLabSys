
import os
from PyExpLabSys.file_parsers.chemstation import Report

# This is the measurement path, should be generated somehow
folderpath = '/home/kenni/Dokumenter/chemstation parser/January2015/def_GC 2015-01-13 11-16-24'


# Look for injection folders (they are the ones that start with NV)
injections = []
for item in os.listdir(folderpath):
    if item.startswith('NV'):
        injections.append(item)
injections.sort()

# Parse all the Report.TXT files in the injections folders
for injection in injections:
    reportpath = os.path.join(folderpath, injection, 'Report.TXT')
    report = Report(reportpath)
    print(report.measurements)
