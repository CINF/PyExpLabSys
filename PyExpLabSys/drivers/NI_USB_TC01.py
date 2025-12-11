import logging
from time import sleep, time

import nidaqmx
from nidaqmx.constants import ThermocoupleType, TemperatureUnits

# Setup logging
LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

class ni_usb_tc01:
    """Driver for the NI USB-TC01 Thermocouple Device."""

    def __init__(self, device_name="Dev1/ai0", thermocouple_type=ThermocoupleType.K):
        self.device_name = device_name
        self.thermocouple_type = thermocouple_type
        self.task = None

    def open(self):
        """Open the device and configure the thermocouple channel."""
        self.task = nidaqmx.Task()
        self.task.ai_channels.add_ai_thrmcpl_chan(
            self.device_name,
            thermocouple_type=self.thermocouple_type,
            units=TemperatureUnits.DEG_C
        )
        LOG.info(f"Opened NI USB-TC01 on {self.device_name} with thermocouple type {self.thermocouple_type}")

    def read_temperature(self):
        """Read the temperature from the thermocouple."""
        if self.task is None:
            raise RuntimeError("Device not opened. Call open() before reading temperature.")
        
        temperature = self.task.read()
        LOG.info(f"Read temperature: {temperature:.2f} °C")
        return temperature

    def close(self):
        """Close the device."""
        if self.task is not None:
            self.task.close()
            self.task = None
            LOG.info("Closed NI USB-TC01 device.")


if __name__ == "__main__":
    tc01 = ni_usb_tc01(device_name="Dev2/ai0", thermocouple_type=ThermocoupleType.K)
    tc01.open()
    try:
        temp = tc01.read_temperature()
        print(f"Temperature: {temp:.2f} °C")
    except Exception as e:
        LOG.error(f"Error reading temperature: {e}")
    tc01.close()
