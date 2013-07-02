import MySQLdb
import time
from datetime import datetime

try:
    db = MySQLdb.connect(host="servcinf", user="cinf_reader",passwd = "cinf_reader", db = "cinfdata")
except:
    db = MySQLdb.connect(host="127.0.0.1", port=9995, user="cinf_reader",passwd = "cinf_reader", db = "cinfdata")

cursor = db.cursor()


f = open('eclab.mpt','r')
s = f.read()
f.close()
rows = s.split('\n')

meta_data = {}
#In general, no chekcs are currently performed to make sure the input file is valid


s = 'Nb header lines :'
for row in rows[0:10]: #Header information should be at the top
    n = row.find(s)
    if row.find(s) > -1:
        meta_data['header_length'] = int(row[len(s):].strip())

s = 'Acquisition started on :'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        timestamp = time.strptime(row[len(s):-1].strip(), '%m/%d/%Y %H:%M:%S')       
        meta_data['timestamp'] = datetime.fromtimestamp(time.mktime(timestamp))
        break


s = 'CE vs. WE compliance from'        
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        n = row.find('to')
        meta_data['cs_vs_we_from'] = int(row[len(s):n-2])
        meta_data['cs_vs_we_to']   = int(row[n+2:-2])
        break

s = 'Electrode connection :'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        meta_data['electrode_connection'] = row[len(s):-1].strip()
        break

s = 'Ewe ctrl range'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        n = row.find('min')
        m = row.find('max')
        meta_data['ewe_ctrl_range_min'] = float(row[n+5:m-3].replace(',','.'))
        meta_data['ewe_ctrl_range_max'] = float(row[m+5:-3].replace(',','.'))
        break

s = 'Ei (V)'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        meta_data['Ei'] = float(row[len(s):].strip().replace(',','.'))
        break

s = 'dE/dt'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        meta_data['dE_dt'] = float(row[len(s):].strip().replace(',','.'))
        break

s = 'E1 (V)'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        meta_data['E1'] = float(row[len(s):].strip().replace(',','.'))
        break

s = 'E2 (V)'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        meta_data['E2'] = float(row[len(s):].strip().replace(',','.'))
        break

s = 'nc cycles'
for row in rows[0:meta_data['header_length']]:
    if row.find(s) > -1:
        meta_data['nc_cycles'] = int(row[len(s):].strip())
        break


order_row = {}
header_row = rows[meta_data['header_length']-1].split('\t')
data_rows = {}
data_rows[0] = ['counter inc', 'time/s', 'control/V', 'Ewe/V', '<I>/mA', 'cycle number']

j = 0
for row in data_rows[0]:
    for i in range(0, len(header_row)):
        if header_row[i].find(row) > -1:
            order_row[j] = i
            j = j+1

i = 1
for row in rows[meta_data['header_length']:]:
    data = row.split('\t')
    tmp_row = []
    for j in range(0, len(order_row)):
        tmp_row.append(data[order_row[j]])
    data_rows[i] = tmp_row
    i = i+1


comment = "First insert"
for label in data_rows[0]:
    query  = 'insert into measurements set timestamp = "' + str(meta_data['timestamp']) + '"'
    query += ', type = 12, label = "' + label + '", comment = "' + comment + '"'
    query += ', ce_vs_we_from = ' + str(meta_data['cs_vs_we_from'])
    query += ', ce_vs_we_to = ' + str(meta_data['cs_vs_we_to'])
    query += ', electrode_connection = "' + meta_data['electrode_connection'] + '"'
    query += ', ewe_ctrl_range_min = ' + str(meta_data['ewe_ctrl_range_min'])
    query += ', ewe_ctrl_range_max = ' + str(meta_data['ewe_ctrl_range_max'])
    query += ', Ei = ' + str(meta_data['Ei'])
    query += ', dE_dt = ' + str(meta_data['dE_dt'])
    query += ', E1 = ' + str(meta_data['E1'])
    query += ', E2 = ' + str(meta_data['E2'])
    query += ', nc_cycles = ' + str(meta_data['nc_cycles'])
    
print query
print len(data_rows)


