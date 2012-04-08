from SCPI import SCPI

class CPX400DPDriver(SCPI):

    def __init__(self):
        SCPI.__init__(self,'/dev/ttyACM0','serial')

