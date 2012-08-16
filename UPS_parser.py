import urllib2
import MySQLdb
import time
from datetime import datetime

def sqlTime():
	sqltime = datetime.now().isoformat(' ')[0:19]
	return(sqltime)

""" Updates the database if time or value is changed significantly"""
def UpdateDatabase(tabel,value,trip_level=2):
    query = "select unix_timestamp(time), value from " + tabel + " order by time desc limit 1"
    db.execute(query)
    res = db.fetchone()
    time_diff = time.time()-res[0]
    value_diff = abs(float(value) - res[1])
    if (time_diff > 1800) or (value_diff>trip_level):
        query = "insert into " + tabel + " set time = \"" + sqlTime() + "\", value = \"" + str(value)  + "\""
        print query
        db.execute(query)


outputUPSurl = 'http://ups-b312.fysik.dtu.dk/UPS/tridout.htm'
normalInputUPSurl = 'http://ups-b312.fysik.dtu.dk/UPS/tridin1.htm'
bypassInputUPSurl = 'http://ups-b312.fysik.dtu.dk/UPS/tridin2.htm'
batteryUPSurl = 'http://ups-b312.fysik.dtu.dk/UPS/tridbat.htm'

connection=MySQLdb.connect(user="ups",passwd="ups",db="cinfdata",host="servcinf")
db=connection.cursor()

try:
    outputUPScontent = urllib2.urlopen(outputUPSurl).read()
    normalInputUPScontent = urllib2.urlopen(normalInputUPSurl).read()
    bypassInputUPScontent = urllib2.urlopen(bypassInputUPSurl).read()
    batteryUPScontent = urllib2.urlopen(batteryUPSurl).read()
except IOError:
    print "Could not get URLs"


WPh1UPS = outputUPScontent[4382:4386]
WPh2UPS = outputUPScontent[4480:4484]
WPh3UPS = outputUPScontent[4578:4582]
UpdateDatabase('ups_WPh1',WPh1UPS)
UpdateDatabase('ups_WPh2',WPh2UPS)
UpdateDatabase('ups_WPh3',WPh3UPS)

kVAPh1UPS = outputUPScontent[4713:4717]
kVAPh2UPS = outputUPScontent[4812:4816]
kVAPh3UPS = outputUPScontent[4911:4915]
UpdateDatabase('ups_kVAPh1',kVAPh1UPS)
UpdateDatabase('ups_kVAPh2',kVAPh2UPS)
UpdateDatabase('ups_kVAPh3',kVAPh3UPS)

currentPh1UPS = outputUPScontent[5017:5019]
currentPh2UPS = outputUPScontent[5078:5080]
currentPh3UPS = outputUPScontent[5139:5141]
UpdateDatabase('ups_currentPh1',currentPh1UPS)
UpdateDatabase('ups_currentPh2',currentPh2UPS)
UpdateDatabase('ups_currentPh3',currentPh3UPS)

phaseVoltagePh1UPS = outputUPScontent[5222:5225]
phaseVoltagePh2UPS = outputUPScontent[5320:5323]
phaseVoltagePh3UPS = outputUPScontent[5418:5421]
UpdateDatabase('ups_phaseVoltagePh1',phaseVoltagePh1UPS)
UpdateDatabase('ups_phaseVoltagePh2',phaseVoltagePh2UPS)
UpdateDatabase('ups_phaseVoltagePh3',phaseVoltagePh3UPS)

voltagePh1UPS = outputUPScontent[5555:5558]
voltagePh2UPS = outputUPScontent[5617:5620]
voltagePh3UPS = outputUPScontent[5679:5682]
UpdateDatabase('ups_voltagePh1',voltagePh1UPS,0)
UpdateDatabase('ups_voltagePh2',voltagePh2UPS,0)
UpdateDatabase('ups_voltagePh3',voltagePh3UPS,0)

current1NormalInputUPS = normalInputUPScontent[2685:2687]
current2NormalInputUPS = normalInputUPScontent[2746:2748]
current3NormalInputUPS = normalInputUPScontent[2807:2809]
UpdateDatabase('ups_current1NormalInput',current1NormalInputUPS)
UpdateDatabase('ups_current2NormalInput',current2NormalInputUPS)
UpdateDatabase('ups_current3NormalInput',current3NormalInputUPS)

voltage1NormalInputUPS = normalInputUPScontent[2890:2893]
voltage2NormalInputUPS = normalInputUPScontent[2988:2991]
voltage3NormalInputUPS = normalInputUPScontent[3086:3089]
UpdateDatabase('ups_voltage1NormalInput',voltage1NormalInputUPS,0)
UpdateDatabase('ups_voltage2NormalInput',voltage2NormalInputUPS,0)
UpdateDatabase('ups_voltage3NormalInput',voltage3NormalInputUPS,0)

frequencyNormalInputUPS = normalInputUPScontent[3372:3376]
UpdateDatabase('ups_frequencyNormalInput',frequencyNormalInputUPS,0)

current1BypassInputUPS = bypassInputUPScontent[2941:2942]
current2BypassInputUPS = bypassInputUPScontent[3002:3003]
current3BypassInputUPS = bypassInputUPScontent[3063:3064]
#This value is not actually logged
#UpdateDatabase('ups_current1BypassInput',current1BypassInputUPS)
#UpdateDatabase('ups_current2BypassInput',current2BypassInputUPS)
#UpdateDatabase('ups_current3BypassInput',current3BypassInputUPS)

voltage1BypassInputUPS = bypassInputUPScontent[3146:3149]
voltage2BypassInputUPS = bypassInputUPScontent[3244:3247]
voltage3BypassInputUPS = bypassInputUPScontent[3342:3345]
#This value is not actually logged
#UpdateDatabase('ups_voltage1BypassInput',voltage1BypassInputUPS)
#UpdateDatabase('ups_voltage2BypassInput',voltage2BypassInputUPS)
#UpdateDatabase('ups_voltage3BypassInput',voltage3BypassInputUPS)

batteryChargeLevelUPS = batteryUPScontent[1962:1965]
batteryVoltageUPS = batteryUPScontent[2142:2145]
batteryTemperatureUPS = batteryUPScontent[2537:2539]
UpdateDatabase('ups_batteryChargeLevel',batteryChargeLevelUPS,0)
UpdateDatabase('ups_batteryVoltageLevel',batteryVoltageUPS,0)
UpdateDatabase('ups_batteryTemperatureLevel',batteryTemperatureUPS,0)
