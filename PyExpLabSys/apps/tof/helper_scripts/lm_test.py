import pickle
import numpy as np
import math
#from numpy import sqrt, pi, exp, linspace, loadtxt
from lmfit import  Model
import matplotlib.pyplot as plt

Data = pickle.load(open('4160.p', 'rb'), encoding='latin1')
times = [5.53]
times = [11.455, 11.468]

center = np.where(Data[:,0] > np.mean(times))[0][0]

Start = center - 125 #Display range
End = center + 125
x = Data[Start:End,0]
y = Data[Start:End,1]

def gaussian(x, amp, cen, wid):
    return amp * math.e ** (-1 * ((x - cen) ** 2) / wid)

def double_gaussian(x, amp, cen, wid, amp2, cen2):
    peak1 = gaussian(x, amp, cen, wid)
    peak2 = gaussian(x, amp2, cen2, wid)
    return peak1 + peak2

if len(times) == 1:
    gmod = Model(gaussian)
    result = gmod.fit(y, x=x, amp=max(y), cen=times[0], wid=0.000001)
if len(times) == 2:
    center1 = np.where(Data[:,0] > times[0])[0][0]
    max1 = max(Data[center1-10:center1+10, 1])

    center2 = np.where(Data[:,0] > times[1])[0][0]
    max2 = max(Data[center2-10:center2+10, 1])
    
    gmod = Model(double_gaussian)
    result = gmod.fit(y, x=x, amp=max1, cen=times[0],
                      amp2=max2, cen2=times[1], wid=0.000002)

print(result.params['amp'].value)

print(result.fit_report())
print(result.success)

plt.plot(x, y,         'bo')
plt.plot(x, result.init_fit, 'k--')
plt.plot(x, result.best_fit, 'r-')
plt.show()
