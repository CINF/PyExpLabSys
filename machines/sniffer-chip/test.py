
from bio_logic import SP150, OCV, TECCParam
import ctypes

def main():
    """ Main method for tests """
    sp150 = SP150('130.225.86.97')
    print sp150.get_lib_version()
    sp150.connect()
    #for n in range(16):
    #    print sp150.is_channel_plugged(n)
    #channels = sp150.get_channels_plugged()
    #print channels
    #print sp150.device_info
    #cid, channel_info = sp150.get_channel_infos(0)
    #for key, _ in channel_info._fields_:
    #    print key, getattr(channel_info, key)
    #print sp150.get_message(0)
    #print sp150.load_firmware(channels)
    #print sp150.get_channel_infos(0)
    sp150.disconnect()

def technique():
    ocv = OCV()
    #print ocv


if __name__ == '__main__':
    #main()
    technique()




