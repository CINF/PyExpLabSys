import scipy
import scipy.ndimage
import time

img = scipy.misc.imread('snapshot.png')

error = ""
k = 0
a = time.time()
for i in range(0,img.shape[0],4):
    for j in range(0,img.shape[1],10):
        #print img[i,j,0]
        #print img[i,j,1]
        #print img[i,j,2]
        if ((img[i,j,0] - 10) > img[i,j,1]):
            if k<50:
                print "0: " + str(img[i,j,0]) + ", 1: " + str(img[i,j,1]) + ", 2: " + str(img[i,j,2])
                k = k + 1

print error
print time.time() -a 
