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

# Get and plot old LoggingCriteriumChecker behaviour
class OldChecker(Checker):
    def pretrig_sorter(self, codename, type_, data_point):
        """Skip pretrig sorting to simulate behaviour of LoggingCriteriumChecker"""
        return

checker = OldChecker(
    codenames=['current'],
    types=[TYPE],
    criteria=[CRITERIUM],
    time_outs=[TIMEOUT],
    )
for x, y in ref_data:
    checker.check('current', y, time_=x)
old_data = np.array(checker.saved_points['current'])

# Plot reference data
plt.figure(1)
plt.title('"Old" model')
plt.plot(ref_data[:, 0], ref_data[:, 1], 'bo-', label='Original data')
plt.plot(old_data[:, 0], old_data[:, 1], 'ro-', label='Original LCC')
plt.xlabel('Time (s)')
plt.ylabel('Current (A)')

class NewChecker(Checker):
    def pretrig_sorter(self, codename, type_, data_point):
        """On pretrig event change logging criterium to 1/10"""
        self.buffer[codename].reverse() # the attribute will be cleared after this algorithm
        latest = data_point
        saved_points = []
        print('Pretrig sorter: {}'.format(latest)) ###
        # Log every point with a "sequential" variation of 10% (of general criterium)
        crit = self.measurements[codename]['criterium'] * 0.10
        for x, y in self.buffer[codename]:
            if type_ == 'lin':
                #print(latest[1] - y, crit)
                if abs(latest[1] - y) > crit:
                    print('adding point: {}'.format((x, y)))
                    saved_points.append((x, y))
                    latest = (x, y)
            else:
                pass # do log version of above
        saved_points.reverse() # fix ordering (this should be done in main function to prevent this sort of mistake)
        for point in saved_points:
            self.saved_points[codename].append(point)

checker = NewChecker(
    codenames=['current'],
    types=[TYPE],
    criteria=[CRITERIUM],
    time_outs=[TIMEOUT],
    )
for x, y in ref_data:
    checker.check('current', y, time_=x)
new_data = np.array(checker.saved_points['current'])

# Data stats
lref = len(ref_data)
lold = len(old_data)
lnew = len(new_data)
print('Number of points in raw data set: {} / 100%'.format(lref))
print('Number of points saved by old LCC: {} / {:1.1}%'.format(lold, lold/lref*100))
print('Number of points saved by new LCC: {} / {:1.1}%'.format(lnew, lnew/lref*100))

# Plot reference data
plt.figure(2)
plt.title('New model')
plt.plot(ref_data[:, 0], ref_data[:, 1], 'bo-', label='Original data')
plt.plot(new_data[:, 0], new_data[:, 1], 'go-', label='New LCC')
plt.xlabel('Time (s)')
plt.ylabel('Current (A)')

plt.legend()
plt.show()
