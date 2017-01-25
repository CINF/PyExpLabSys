import subprocess
import time

while True:
    print 'Starting'
    retur = subprocess.check_output(['gphoto2', '--set-config', '/main/imgsettings/iso=2']) #ISO:
    print 'Iso chosen'
    retur = subprocess.check_output(['gphoto2', '--set-config', '/main/capturesettings/shutterspeed=10']) #Shutterspeed: 1/?
    print 'Shutterspeed chosen'
    retur = subprocess.check_output(['gphoto2', '--set-config', '/main/capturesettings/aperture=14']) #Aperture: ?
    print 'Aperture chosen'
    retur = subprocess.check_output(['gphoto2', '--capture-image-and-download'])
    print 'Image aquired'
    retur = subprocess.check_output(['mv', 'capt0000.jpg', '/usr/share/mini-httpd/html/'])
    print 'Finished'
    time.sleep(600)
