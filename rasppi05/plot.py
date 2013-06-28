import pickle
import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
from mpl_toolkits.mplot3d import axes3d

klaf = open('data.pkl','rb')
data = pickle.load(klaf)
klaf.close()

x = range(0,len(data[:,0,0]))
y = range(0,len(data[0,:,0]))
low = interpolate.interp2d(x, y, data[:,:,0], kind='cubic')

a = range(0,100)
b = range(0,100)
z = np.zeros((100,100))
for i in range(0,100):
    for j in range(0,100):
        z[i,j] = low(i/4.0,j/4.0)
A, B = np.meshgrid(a,b)
print A.shape
print B.shape
print z.shape

Y, X = np.meshgrid(y,x)

print X.shape
print Y.shape
print data[:,:,0].shape

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.plot_wireframe(X, Y, data[:,:,0], rstride=1, cstride=1)
ax.plot_wireframe(X, Y, data[:,:,1], rstride=1, cstride=1, color='r')

#ax.plot_wireframe(A, B, z, rstride=1, cstride=1)

plt.show()
