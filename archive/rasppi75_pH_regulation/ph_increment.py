
import time
import argparse

from PyExpLabSys.drivers.omegabus import OmegaBus
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
from PyExpLabSys.drivers.wpi_al1000 import AL1000

from PyExpLabSys.auxiliary.pid import PID

#Define running time
minutes = 25

def current_to_ph(value):
    """Convert current in milliamps between 4 and 20 to Ph between 0 and 14"""
    slope = 14/16
    ph = (value - 4) * slope
    return ph

def run(pump_second, pump_main, obus, pid, data_set_saver, time_start, setpoint, rate_second, rate_main, rate_second_offset, rate_main_offset, rate_second_min, rate_second_max, direction, minutes):
    """Runs the PID and reports data"""
#    n = 0  #Only for use with ramping main pump speed
    while True:
        
        if time.time()-time_start > 60*minutes or time.time()-time_start == 60*minutes:
            print("Program done")
            break
        #        n = n + 1
        #Read and log pH value and setpoint
        
        value = obus.read_value(1)
        value = current_to_ph(value)
        print("pH: " + str(round(value,3)))
        data_set_saver.save_point("ph_value", (time.time()-time_start, value))
        data_set_saver.save_point("ph_setpoint",(time.time()-time_start, setpoint))

        #Log PID contributions and pump rate
        data_set_saver.save_point("p_korr", (time.time()-time_start, pid.proportional_contribution()))
        data_set_saver.save_point("i_korr", (time.time()-time_start, pid.integration_contribution()))
        data_set_saver.save_point("total_korr", (time.time()-time_start, pid.proportional_contribution()+
                                  pid.integration_contribution()))
        data_set_saver.save_point("pump_rate", (time.time()-time_start,pump_second.get_rate()))

        # For direction = up <=> setpoint > 7
        if direction == "up":
            if value > setpoint-0.5 or value == setpoint-0.5:
                #Kick in-functionality
                if rate_main == 0:
                    pump_main.set_rate(round(rate_main_offset,3))
                    pump_main.start_program()
                    rate_main = rate_main_offset
                #Standard functionality
                rate_second += pid.wanted_power(value)
                if rate_second < rate_second_min:
                    rate_second = rate_second_min
                if rate_second > rate_second_max:
                    rate_second = rate_second_max

        # For direction = down <=> setpoint < 7 or setpoint = 7
        if direction == "down":
            if value < setpoint+2 or value == setpoint+2:
                #Kick in-functionality
                if rate_second == 0:
                    pump_second.set_rate(round(rate_second_offset,3))
                    pump_second.start_program()
                    rate_second = rate_second_offset
                    continue
                #Standard functionality
                rate_second += pid.wanted_power(value)
                if rate_second < rate_second_min:
                    rate_second = rate_second_min
                if rate_second > rate_second_max:
                    rate_second = rate_second_max

        #Set new rate
        pump_second.set_rate(round(rate_second,3))
        print("Rate: " + str(round(rate_second, 3)))

        #Set ramp of main pump (optional)
#        if n>16 and n % 4 == 0 and rate_main < 2:
#            rate_main  += 0.1
#            print("time= " + str(time.time() - time_start))
#            pump_main.set_rate(round(rate_main,3))

def main():
    """Main function"""

    parser = argparse.ArgumentParser(description='Run the infamous ph control script.')
    # ph_setpoint, ph_direction (string [up, down]), kick_in_rate (float)

    # Main (constant), secondary (regulation)
    
    # python ph_increment.py 10.0 --direction up --main-offset=24.0 --second-min=10.0 --second-max=40.0 --second-offset=17.0
    parser.add_argument('setpoint', type=float, help='The Ph setpoint.')
    parser.add_argument('--direction', default=None, help='Pumping direction. Must be up or down.', required=True)
    parser.add_argument('--main-offset', type=float, default=None, help='Start pumping speed for the main pump.', required=True)
    parser.add_argument('--second-min', type=float, default=None, help='Minimum pumping speed for the secondary pump.', required=True)
    parser.add_argument('--second-max', type=float, default=None, help='Maximum pumping speed for the secondary pump.', required=True)
    parser.add_argument('--second-offset', type=float, default=None, help='Start pumping value for the secondary pump.', required=True)
    parser.add_argument('--comment',  default=None, help='Optional comment', required=True)

    args = parser.parse_args()

    ## Edit comment
    comment ="pH "+ str(args.setpoint) + " // p: 0.02 // start rate " + str(args.second_offset) + " // " +  args.comment
    ## Edit comment
    
#    raise SystemExit('All good')
    # Init pumps, Omegabus, PID and data saver
    pump_main = AL1000("/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTV9X9TM-if00-port0")
    pump_second = AL1000("/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWZCJLU-if00-port0")
    obus = OmegaBus(
        "/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWZCGSW-if00-port0",
        baud=9600,
    )
    data_set_saver = DataSetSaver("measurements_dummy", "xy_values_dummy", "dummy", "dummy")
    pid = PID(pid_p=0.04, pid_i=0.0, pid_d=0, p_max=9999, p_min=-9)
    pid.update_setpoint(args.setpoint)
#    time_start = time.time()

    #Pre flight check. 
    pump_main_check = pump_main.get_firmware()
    print("main: "+pump_main_check)
    pump_second_check = pump_second.get_firmware()
    print("second: " +pump_second_check)
    obus_check = obus.read_value(1)
    obus_check = current_to_ph(obus_check)
    if pump_main_check != "NE1000V3.923":
        print("Main pump failed")
        raise SystemExit(1)
    if pump_second_check != "NE1000V3.923":
        print("Secondary pump failed")
        raise SystemExit(1)
    if obus_check < 0:
        print("OmegaBus failed")
        raise SystemExit(1)

    #Set initial condition for pumps
    pump_second.set_direction("INF")
    pump_main.set_direction("INF")
    if args.direction == "up":
        pump_second.set_rate(args.second_offset)
        rate_second = args.second_offset
        pump_main.set_rate(0)
        rate_main = 0
    if args.direction == "down":
        pump_second.set_rate(0)
        rate_second = 0
        pump_main.set_rate(args.main_offset)
        rate_main = args.main_offset
    
    pump_second.set_vol(9999)
    pump_main.set_vol(9999)
    pump_second.start_program()
    pump_main.start_program()

    # Setup database saver
    data_set_saver.start()
    data_set_time = time.time()
    metadata = {"Time": CustomColumn(data_set_time, "FROM_UNIXTIME(%s)"), "comment": comment,
    "type": 64, "preamp_range": 0, "sem_voltage": 0}
    for label in ["p_korr", "i_korr", "total_korr", "ph_setpoint", "ph_value", "pump_rate"]:
        metadata["mass_label"] = label
        data_set_saver.add_measurement(label, metadata)

    # Run PID
    try:
        time_start = time.time()
        run(pump_second, pump_main, obus, pid, data_set_saver, time_start, args.setpoint, rate_second, rate_main, args.second_offset, args.main_offset, args.second_min , args.second_max, args.direction, minutes)
        
    except KeyboardInterrupt:
        # Clean up
        pump_main.set_rate(0)
        pump_second.set_rate(0)
        pump_main.stop_program()
        pump_second.stop_program()
        data_set_saver.stop()
        raise SystemExit(" Sequence stopped.")

    # Clean up
    pump_main.set_rate(0)
    pump_second.set_rate(0)
    pump_main.stop_program()
    pump_second.stop_program()
    # Log pH during ageing
    try:
        while True:
            value = obus.read_value(1)
            value = current_to_ph(value)
            print("pH: " + str(round(value,3)))
            data_set_saver.save_point("ph_value", (time.time()-time_start, value))
            data_set_saver.save_point("ph_setpoint",(time.time()-time_start, args.setpoint))
            time.sleep(8)
    except KeyboardInterrupt:
        data_set_saver.stop()

    pass

if __name__ == "__main__" :
    main()
