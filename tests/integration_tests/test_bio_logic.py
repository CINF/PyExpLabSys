"""Integration tests for the biologic SP-150 driver"""

from __future__ import print_function
from pprint import pprint
import time
from PyExpLabSys.drivers.bio_logic import SP150, OCV, CP, CA, CV, CVA, SPEIS


def basic():
    """ Main method for tests """
    sp150 = SP150('10.54.6.74')
    print('## Device info before connect:', sp150.device_info)

    print('\n## Lib version:', sp150.get_lib_version())
    dev_info = sp150.connect()
    print('\n## Connect returned device info:')
    pprint(dev_info)

    # Information about whether the channels are plugged
    channels = sp150.get_channels_plugged()
    print('\n## Channels plugged:', channels)
    for index in range(16):
        print('Channel {} plugged:'.format(index),
              sp150.is_channel_plugged(index))

    print('\n## Device info:')
    pprint(sp150.device_info)

    channel_info = sp150.get_channel_infos(0)
    print('\n## Channel 0 info')
    pprint(channel_info)

    print('\n## Load_firmware:', sp150.load_firmware(channels))

    print('\n## Message left in the queue:')
    while True:
        msg = sp150.get_message(0)
        if msg == '':
            break
        print(msg)

    sp150.disconnect()
    print('\n## Disconnect and test done')


def current_values():
    """Test the current values method"""
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    current_values_ = sp150.get_current_values(0)
    pprint(current_values_)
    sp150.disconnect()


def mess_with_techniques():
    """Test adding techniques"""
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    ocv = OCV(rest_time_T=0.3,
              record_every_dE=10.0,
              record_every_dT=0.01)
    sp150.load_technique(0, ocv, False, False)
    sp150.load_technique(0, ocv, True, True)
    #sp150.load_technique(0, ocv, False, True)
    print(sp150.get_channel_infos(0)['NbOfTechniques'])
    sp150.disconnect()


def test_ocv_technique():
    """Test the OCV technique"""
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    ocv = OCV(rest_time_T=0.2,
              record_every_dE=10.0,
              record_every_dT=0.01)
    sp150.load_technique(0, ocv)
    sp150.start_channel(0)
    try:
        time.sleep(0.1)
        while True:
            data_out = sp150.get_data(0)
            if data_out is None:
                break
            print(data_out.Ewe)
            print(data_out.Ewe_numpy)
            time.sleep(0.1)
    except KeyboardInterrupt:
        sp150.stop_channel(0)
        sp150.disconnect()
    else:
        sp150.stop_channel(0)
        sp150.disconnect()


def test_cp_technique():
    """Test the CP technique"""
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    cp_ = CP(current_step=(-1E-6, -10E-6, -100E-6),
             vs_initial=(False, False, False),
             duration_step=(2.0, 2.0, 2.0),
             record_every_dE=1.0,
             record_every_dT=1.0)
    sp150.load_technique(0, cp_)
    #sp150.disconnect()
    #return

    sp150.start_channel(0)
    try:
        while True:
            time.sleep(2)
            data_out = sp150.get_data(0)
            if data_out is None:
                break
            #print(data_out.Ewe)
            print(data_out.I_numpy)
            print('NP:', data_out.cycle_numpy)
    except KeyboardInterrupt:
        sp150.stop_channel(0)
        sp150.disconnect()
    else:
        sp150.stop_channel(0)
        sp150.disconnect()


def test_ca_technique():
    """Test the CA technique"""
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    ca_ = CA(voltage_step=(0.01, 0.02, 0.03),
             vs_initial=(False, False, False),
             duration_step=(5.0, 5.0, 5.0),
             record_every_dI=1.0,
             record_every_dT=0.1)
    sp150.load_technique(0, ca_)
    #sp150.disconnect()
    #return

    sp150.start_channel(0)
    try:
        while True:
            time.sleep(5)
            data_out = sp150.get_data(0)
            if data_out is None:
                break
            print(data_out.technique)
            print('Ewe:', data_out.Ewe)
            print('I:', data_out.I)
            print('cycle:', data_out.cycle)
    except KeyboardInterrupt:
        sp150.stop_channel(0)
        sp150.disconnect()
    else:
        sp150.stop_channel(0)
        sp150.disconnect()


def test_cv_technique():
    """Test the CV technique"""
    import matplotlib.pyplot as plt
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    cv_ = CV(vs_initial=(True,) * 5,
             voltage_step=(0.0, 0.5, -0.7, 0.0, 0.0),
             scan_rate=(10.0,) * 5,
             record_every_dE=0.01,
             N_cycles=3)
    sp150.load_technique(0, cv_)

    sp150.start_channel(0)
    ew_ = []
    ii_ = []
    try:
        while True:
            time.sleep(0.1)
            data_out = sp150.get_data(0)
            if data_out is None:
                break
            print(data_out.technique)
            print('Ewe:', data_out.Ewe)
            print('I:', data_out.I)
            ew_ += data_out.Ewe
            ii_ += data_out.I
            print('cycle:', data_out.cycle)
    except KeyboardInterrupt:
        sp150.stop_channel(0)
        sp150.disconnect()
    else:
        sp150.stop_channel(0)
        sp150.disconnect()
    plt.plot(ew_, ii_)
    plt.show()
    print('end')


def test_cva_technique():
    """Test the CVA technique"""
    import matplotlib.pyplot as plt
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    print('kk')
    cva = CVA(
        vs_initial_scan=(False,) * 4,
        voltage_scan=(0.0, 0.2, -0.2, 0.0),
        scan_rate=(50.0,) * 4,
        vs_initial_step=(False,) * 2,
        voltage_step=(0.1,) * 2,
        duration_step=(1.0,) * 2,
    )
    sp150.load_technique(0, cva)

    sp150.start_channel(0)
    ew_ = []
    ii_ = []
    try:
        while True:
            time.sleep(0.1)
            data_out = sp150.get_data(0)
            if data_out is None:
                break
            print(data_out.technique)
            print('time:', data_out.time,
                  'numpy', data_out.time_numpy, data_out.time_numpy.dtype)
            print('I:', data_out.I)
            print('Ec:', data_out.Ec)
            print('Ewe:', data_out.Ewe)
            print('Cycle:', data_out.cycle,
                  'numpy', data_out.cycle_numpy, data_out.cycle_numpy.dtype)
            ew_ += data_out.Ewe
            ii_ += data_out.I
    except KeyboardInterrupt:
        sp150.stop_channel(0)
        sp150.disconnect()
    else:
        sp150.stop_channel(0)
        sp150.disconnect()
    plt.plot(ew_, ii_)
    plt.show()
    print('end')


def test_speis_technique():
    """Test the SPEIS technique"""
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    print('kk')
    speis = SPEIS(
        vs_initial=False, vs_final=False,
        initial_voltage_step=0.1,
        final_voltage_step=0.2,
        duration_step=1.0,
        step_number=3,
        final_frequency=100.0E3, initial_frequency=10.0E3,
        I_range='KBIO_IRANGE_1mA'
    )
    sp150.load_technique(0, speis)
    sp150.start_channel(0)

    try:
        while True:
            time.sleep(0.1)
            data_out = sp150.get_data(0)
            if data_out is None:
                break
            print('Technique', data_out.technique)
            print('Process index', data_out.process)
            if data_out.process == 0:
                print('time', data_out.time)
                print('Ewe', data_out.Ewe)
                print('I', data_out.I)
                print('step', data_out.step)
            else:
                print('freq', data_out.freq)
                print('abs_Ewe', data_out.abs_Ewe)
                print('abs_I', data_out.abs_I)
                print('Phase_Zwe', data_out.Phase_Zwe)
                print('Ewe', data_out.Ewe)
                print('I', data_out.I)
                print('abs_Ece', data_out.abs_Ece)
                print('abs_Ice', data_out.abs_Ice)
                print('Phase_Zce', data_out.Phase_Zce)
                print('Ece', data_out.Ece)
                print('t', data_out.t)
                print('Irange', data_out.Irange)
                print('step', data_out.step)
    except KeyboardInterrupt:
        sp150.stop_channel(0)
        sp150.disconnect()
    else:
        sp150.stop_channel(0)
        sp150.disconnect()
    print('end')


if __name__ == '__main__':
    #basic()
    #current_values()
    #test_ocv_technique()
    #test_cp_technique()
    #test_ca_technique()
    #test_cv_technique()
    #test_cva_technique()
    test_speis_technique()
    #test_message()
