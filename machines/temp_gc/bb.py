

from __future__ import print_function

import os


from PyExpLabSys.file_parsers.chemstation import Sequence
import json

# 58273


def scan_for_injections():
    injections = set()

    n = 0
    for root, dirs, files in os.walk("/mnt/big/parser_data/chemstation parser/Data/"):
        n += 1
        if n % 1000 == 0:
            print(n)
        for dir_ in dirs:
            if root not in injections and dir_.endswith('.D'):
                injections.add(root)
                break

    with open('injections', 'wb') as file_:
        json.dump(list(injections), file_)


with open('injections', 'rb') as file_:
    sequences = set(json.load(file_))

print()

total_n_floats = 0

no_injections = []
for number, sequence in enumerate(sequences):
    print(sequence)
    if number % 10 == 0:
        print(number, "of", len(sequences))
    try:
        seq = Sequence(sequence)
    except ValueError as e:
        if str(e).startswith('No injection'):
            no_injections.append(sequence)
            continue
        else:
            raise

    for inj in seq.injections:
        for chfile in inj.raw_files.values():
            total_n_floats += len(chfile.times)
            total_n_floats += len(chfile.values)
        

print('NOO')
print(no_injections)
print("Bytes", total_n_floats)
print("MBytes", float(total_n_floats) / 1048576)


#print(time.time() - s)
1/0

sequence = Sequence('/mnt/big/parser_data/chemstation parser/Data/20170702_Ni5Ga3_SiO2_N2_bpkn')

#print(sequence.injections)
injection = sequence.injections[77]
fid1a = injection.raw_files['FID1A.ch']
tcd2b = injection.raw_files['TCD2B.ch']

#plt.plot(fid1a.values)
plt.plot(tcd2b.values)
plt.show()
#plt.plot(fid1a.values[:, 0], fid1a.values[:, 1])
