
*********************************************
The communications_collecting_pyserial module
*********************************************

This module contains components to collect serial communications "traces" and replay them during
tests.

The :class:`.CommunicationsCollectingSerial` class is used as a drop-in replacement for
:class:`pyserial.Serial` and will collect the communications traces, so they can be saved after the
communication has ended. It is used along of this::

    """Collect communications traces and results"""

    from json import dump
    from pathlib import Path

    from serial import PARITY_NONE

    from somemodule import SomeDriver
    from PyExpLabSys.auxiliary.communications_collecting_pyserial import CommunicationsCollectingSerial

    THIS_DIR = Path(__file__).parent
    DATA_DIR = THIS_DIR / "serial_com_data_folder"
    DATA_DIR.mkdir(exist_ok=True, parents=True)

    com = CommunicationsCollectingSerial(
        port="COM25",
        baudrate=9600,
        bytesize=8,
        parity=PARITY_NONE,
        stopbits=1,
        xonxoff=False,
    )
    driver = SomeDriver(com, address=1)
    collected_test_results = {}


    # Collect return value and communications trace and save
    collected_test_results["some_value"] = driver.get_some_value()
    com.save_collected_coms(DATA_DIR / "some_value.trace")
    com.reset_collected_coms()

    # ... Collect more traces and results

    # Save results
    with open(DATA_DIR / "results.json", "w") as file_:
        dump(collected_test_results, file_, indent=4)

    com.close()

The test around this collected data, using the :class:`.CommunicationsReplayingSerial` might look
like this::

    """Communications traces tests"""

    from json import load
    from pathlib import Path

    from pytest import approx, fixture

    from some_module import SomeDriver
    from PyExpLabSys.auxiliary.communications_collecting_pyserial import CommunicationsReplayingSerial

    THIS_DIR = Path(__file__).parent
    DATA_DIR = THIS_DIR / "serial_com_data_folder"


    @fixture
    def test_data():
        with open(DATA_DIR / "results.json") as file_:
            return load(file_)


    def test_get_value(test_data):
        replaying_coms = CommunicationsReplayingSerial()
        replaying_coms.load_collected_coms(DATA_DIR / "some_value.trace")
        device = SomeDriver(replaying_coms, address=1)
        # NOTE: The reading from the replaying coms has additional assert that the communications is as
        # expected
        assert device.get_some_value() == approx(test_data["some_value"])

Auto-generated module documentation
-----------------------------------

.. automodule:: PyExpLabSys.auxiliary.communications_collecting_pyserial
    :members:
    :member-order: bysource
    :show-inheritance:
