import cv

c = cv.CaptureFromCAM(0)
cv.SetCaptureProperty(c,cv.CV_CAP_PROP_FRAME_WIDTH,320)
cv.SetCaptureProperty(c,cv.CV_CAP_PROP_FRAME_HEIGHT,240)
f = cv.QueryFrame(c)
cv.SaveImage('snapshot.png',f)
print('snapshot.png')
print cv.GetCaptureProperty(c,cv.CV_CAP_PROP_FRAME_WIDTH)
print cv.GetCaptureProperty(c,cv.CV_CAP_PROP_BRIGHTNESS)
