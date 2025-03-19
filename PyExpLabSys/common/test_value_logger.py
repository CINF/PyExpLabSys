from cinfdata import Cinfdata # https://github.com/CINF/cinf_database/blob/master/cinf_database/cinfdata.py
from value_logger import EjlaborateLoggingCriteriumChecker as Checker
import matplotlib.pyplot as plt
import numpy as np

# Constants used for criterium checker
TYPE = 'lin' # lin/log
TIMEOUT = 60 # seconds
CRITERIUM = 5e-12 # Ampere in this example

# Get reference data
db = Cinfdata('omicron', use_caching=True)
ref_data = db.get_data(29472)

# Overwrite default event handler to simulate old LoggingCriteriumChecker behaviour
class OldChecker(Checker):
    def event_handler(self, codename, type_, data_point):
        """Skip pretrig sorting to simulate behaviour of LoggingCriteriumChecker"""
        return

# Run on data set
checker = OldChecker(
    codenames=['current'],
    types=[TYPE],
    criteria=[CRITERIUM],
    time_outs=[TIMEOUT],
    )
for x, y in ref_data:
    checker.check('current', y, time_=x)
old_data = np.array(checker.get_data('current'))

# Plot reference data
plt.figure(1)
plt.title('"Old" model')
plt.plot(ref_data[:, 0], ref_data[:, 1], 'bo-', label='Original data')
plt.plot(old_data[:, 0], old_data[:, 1], 'ro-', label='Original LCC')
plt.xlabel('Time (s)')
plt.ylabel('Current (A)')

# Use default event handler
checker = Checker(
    codenames=['current'],
    types=[TYPE],
    criteria=[CRITERIUM],
    time_outs=[TIMEOUT],
    )
for x, y in ref_data:
    checker.check('current', y, time_=x)
new_data = np.array(checker.get_data('current'))

# Data stats
lref = len(ref_data)
lold = len(old_data)
lnew = len(new_data)
print('Number of points in raw data set: {} / 100%'.format(lref))
print('Number of points saved by old LCC: {} / {:1.1f}%'.format(lold, lold/lref*100))
print('Number of points saved by new LCC: {} / {:1.1f}%'.format(lnew, lnew/lref*100))

# Plot reference data
plt.figure(2)
plt.title('New model')
plt.plot(ref_data[:, 0], ref_data[:, 1], 'bo-', label='Original data')
plt.plot(new_data[:, 0], new_data[:, 1], 'go-', label='New LCC')
plt.xlabel('Time (s)')
plt.ylabel('Current (A)')

plt.legend()
plt.show()
