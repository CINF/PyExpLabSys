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

# Extract month difference from args
difference = 0
if len(sys.argv) > 1:
    try:
        difference = int(sys.argv[1])
    except ValueError:
        print("Argument must be negative integer. IGNORED.")


# For current month the current day is not shown, but it is for old months, so adjust that
cal = calendar.Calendar()
now = datetime.now()
year = now.year
month = now.month
end_day_to_list = now.day
if difference != 0:
    if now.month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    end_day_to_list = calendar.monthrange(year, month)[1] + 1
    print("#############################")
    print("# Showing stats for {}-{:0>2} #".format(year, month))
    print("#############################")



# NOTE in Python 0 is monday. List of (daynumber, weekday)
days = []
for daynumber in range(1, end_day_to_list):
    #print(year, month, daynumber, 12)
    day = datetime(year, month, daynumber, 12)
    days.append((daynumber, day.weekday()))

conn = sqlite3.connect('/home/kenni/.local/share/hamster-applet/hamster.db')
c = conn.cursor()

# Select depending on whether it is current month or not
if difference == 0:
    query = (
        "SELECT "
        "    date(start_time), "
        "    cast(strftime(\"%d\", start_time) as int), "
        "    (JulianDay(end_time) - JulianDay(start_time)) * 24, "
        "    name "
        "FROM "
        "    facts "
        "INNER JOIN "
        "    activities ON facts.activity_id = activities.id "
        "WHERE "
        "    date(start_time) >= date('now','start of month') AND "
        "    date(start_time) < date('now')"
    )
else:
    query = (
        "select "
        "    date(start_time), "
        "    cast(strftime(\"%d\", start_time) as int), "
        "    (JulianDay(end_time) - JulianDay(start_time)) * 24, "
        "    name "
        "FROM "
        "    facts "
        "INNER JOIN "
        "    activities ON facts.activity_id = activities.id "
        "WHERE "
        "    strftime('%Y', start_time) == '{0}' and "
        "    strftime('%m', start_time) == '{1:0>2}'"
    ).format(year, month)


# Collect work hours and categories, 0 is sunday
c.execute(query)
hours_worked = defaultdict(float)
categories = defaultdict(set)
for line in c.fetchall():
    _, daynumber, hours, name = line
    categories[daynumber].add(name)
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

if number_of_workdays + number_of_workdays_with_hours == 0:
    print("No days yet in this month to do statistics on")
    sys.exit(0)

# Print out the table
print("########################################")
print("Table")
last_week_day = None
printed_line = False
for daynumber, weekday in days:
    if last_week_day is None or weekday < last_week_day:
        if not printed_line:
            print("---------------------------")
            printed_line = True
    else:
        printed_line = False
    last_week_day = weekday
        
    if daynumber not in hours_worked:
        continue
    print("{: <9} {: <2} has {: >4.1f} hours ({})".format(
        calendar.day_name[weekday],
        daynumber,
        hours_worked[daynumber],
        ', '.join(categories[daynumber]),
    ))
print("########################################")
print("Totals")
print("{:.1f} hours per work days            ({} of those) Flex: {:+.1f}".format(
    sum_ / number_of_workdays,
    number_of_workdays,
    sum_ - number_of_workdays * 7.4,
))
print("{:.1f} hours per work days with hours ({} of those) Flex: {:+.1f}".format(
    sum_ / number_of_workdays_with_hours,
    number_of_workdays_with_hours,
    sum_ - number_of_workdays_with_hours * 7.4,
))
