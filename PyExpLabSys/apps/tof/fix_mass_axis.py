#import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import MySQLdb
from scipy import optimize
from scipy import interpolate
import math

db = MySQLdb.connect(host="servcinf", user="cinf_reader",passwd = "cinf_reader", db = "cinfdata")
cursor = db.cursor()
cursor.execute("SELECT x*1000000,y FROM xy_values_tof where measurement = 2668")
Data = np.array(cursor.fetchall())

fig = plt.figure()

fit_values = {}
fit_values[2.014] = 4.37
fit_values[4.002602] = 6.1
fit_values[18.01056] = 12.74
fit_values[28] = 15.85
fit_values[39.962] = 18.9
fit_values[43.9898] = 19.81
fit_values[57] = 22.55
fit_values[71] = 25.14
fit_values[85] = 27.5
fit_values[97] = 29.36
fit_values[109] = 31.11
#fit_values['times'] = [4.380, 6.1, 12.74, 15.85, 18.9, 19.81]
#fit_values['masses'] = [2, 4, 18, 28, 40, 44]

i = 0
for mass in fit_values:
    i = i + 1
    ax = fig.add_subplot(4, 3, i)
    center = np.where(Data[:,0] > fit_values[mass])[0][0]
    Start = center -50 #Display range
    End = center + 50
    X_values = Data[Start:End,0]
    Y_values = Data[Start:End,1]
    center = np.where(Y_values == max(Y_values))[0][0]
    
    #Fitting range
    x_values = X_values[center-5:center+5]
    y_values = Y_values[center-5:center+5]

    ax.plot(X_values, Y_values, 'b-')
    ax.axvline(x=X_values[center-5], color='k')
    ax.axvline(x=X_values[center+5], color='k')
    fitfunc = lambda p, x: p[0]*math.e**(-1*((x-fit_values[mass]-p[2])**2)/p[1])       # Target function
    errfunc = lambda p, x, y: fitfunc(p, x) - y # Distance to the target function
    p0 = [50, 0.00001, 0] # Initial guess for the parameters
    p1, success = optimize.leastsq(errfunc, p0[:], args=(x_values, y_values),maxfev=1000) 
    print p1
    ax.plot(X_values, fitfunc(p1, X_values), 'r-')
    fit_values[mass] = fit_values[mass] + p1[2]
print fit_values
plt.show()

# Now we now the exact position of a number of peaks
#fitfunc = lambda p, x: p[0] + p[1]* pow(x, np.int64(2))
fitfunc = lambda p, x: p[0] + p[1]* pow(x, p[2])
errfunc = lambda p, x, y: fitfunc(p, x) - y # Distance to the target function
p0 = [-0.01, 0.1, 2] # Initial guess for the parameters
p1, success = optimize.leastsq(errfunc, p0[:], args=(fit_values.values(), fit_values.keys()), maxfev=1000)
print p1

fig = plt.figure()
ax = fig.add_subplot(2, 1, 1)
ax.plot(fit_values.values(), fit_values.keys() - fitfunc(p1, fit_values.values()), 'bo')
ax = fig.add_subplot(2, 1, 2)
x_fit = np.arange(0, 45, 0.01)
ax.plot(fit_values.values(), fit_values.keys(), 'bo')
ax.plot(x_fit, fitfunc(p1, x_fit), 'k-')
plt.show()

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
ax.plot(fitfunc(p1, Data[:,0]), Data[:,1], 'k-')
#ax.plot(Data[:,0], Data[:,1], 'k-')
ax.set_xlim(1,200)


plt.show()
