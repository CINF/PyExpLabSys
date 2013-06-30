def find_line(string, substring, number=1):
    n = 0
    for i in range(0,number):
        n = string.find(substring, n+1)
        m = string.find('\n',n)
    return string[n:m]

f = open('eclab.mpt','r')
s = f.read()
f.close()

print find_line(s, 'Nb header lines :')
	
print find_line(s, 'CE vs. WE compliance from')
print find_line(s, 'Electrode connection')
print find_line(s, 'Ewe ctrl range')
print find_line(s, 'Ei (V)')
print find_line(s, 'dE/dt')
print find_line(s, 'E1 (V)')
print find_line(s, 'E2 (V)')
print find_line(s, 'nc cycles')

n = s.count('Modify on :')
for i in range(1,n+1):
    print find_line(s, 'Modify on :', i)
    print find_line(s, 'dE/dt', i)
    #print find_line(s, 'Modify on')
    #print find_line(s, 'dE/dt')

header = find_line(s, 'mode')
header = header.split('\t')

relevant_rows = ['counter inc', 'time/s', 'control/V', 'Ewe/V', '<I>/mA', 'cycle number']
for row in relevant_rows:
    for i in range(0, len(header)):
        if header[i].find(row) > -1:
            print header[i]
            print i

last_header_line = s.find(relevant_rows[0])
last_header_char = s.find('\n', last_header_line)



n = last_header_char
while n > 0:
    n = s.find('\n', n+1)
