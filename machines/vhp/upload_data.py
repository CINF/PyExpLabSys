from __future__ import print_function
import os
from PyExpLabSys.file_parsers.chemstation import Sequence

# This is the measurement path, should be generated somehow
basefolder = '/home/kenni/Dokumenter/chemstation parser'

sequence_identifyer = 'sequence.acaml'

sequencefolders = []

for root, dirs, files in os.walk(basefolder):
   if sequence_identifyer in files:
       sequencefolders.append(root)
       
sequences = []
for sequencefolder in sequencefolders:
     sequences.append(Sequence(sequencefolder))
     break

        


