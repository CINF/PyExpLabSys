#!/usr/bin/env python3


"""Small script to extract work time status from hamster applet sqlite database"""

import sys
import sqlite3
from datetime import datetime, timedelta
import calendar
from collections import defaultdict

if sys.version_info.major < 3:
    print("NO! Use Python 3")
    sys.exit(1)

cal = calendar.Calendar()

now = datetime.now()

# NOTE in Python 0 is monday
days = []
for daynumber in range(1, now.day):
    day = datetime(now.year, now.month, daynumber, 12)
    days.append((daynumber, day.weekday()))
#print(days)

conn = sqlite3.connect('/home/kenni/.local/share/hamster-applet/hamster.db')
c = conn.cursor()

query = (
    "select "
    "    date(start_time), "
    "    cast(strftime(\"%d\", start_time) as int), "
    "    (JulianDay(end_time) - JulianDay(start_time)) * 24 "
    "from facts "
    "where date(start_time) >= date('now','start of month') AND "
    "date(start_time) < date('now')"
)

# 0 is sunday
c.execute(query)
hours_worked = defaultdict(float)
for line in c.fetchall():
    datestring, daynumber, hours = line
    hours_worked[daynumber] += hours

# Do the rest of the math
sum_ = sum(hours_worked.values())
number_of_workdays = 0
number_of_workdays_with_hours = 0
workday_range = range(0, 5)
for daynumber, weekday in days:
    if weekday in workday_range:
        number_of_workdays += 1
        if daynumber not in hours_worked:
            print(
                "WARNING. {} {} has no hours".format(
                    calendar.day_name[weekday],
                    daynumber,
                )
            )
        else:
            number_of_workdays_with_hours += 1

print("########################################")
print("Table")
for daynumber, weekday in days:
    if daynumber not in hours_worked:
        continue
    print("{: <9} {: <2} has {: >4.1f} hours".format(
        calendar.day_name[weekday],
        daynumber,
        hours_worked[daynumber]
    ))
print("########################################")
print("Totals")
print("{:.1f} hours per work days".format(sum_ / number_of_workdays))
print("{:.1f} hours per work days with hours".format(sum_ / number_of_workdays_with_hours))

balance = sum_ - number_of_workdays * 7.4
print("Flex balance from this month {:.1f}".format(balance))

