"""This module contains a drop-in replacement for pyserial.Serial which makes it possible to
record communications

"""
from json import dump, load
from pathlib import Path
import base64
from attr import define, asdict
from serial import Serial


@define
class _Communication:
    type: str
    data: bytes

    def as_json(self) -> dict[str, str]:
        dict_ = asdict(self)
        dict_["data"] = base64.standard_b64encode(dict_["data"]).decode("ascii")
        return dict_

    @classmethod
    def from_json(cls, dict_: dict[str, str]) -> "_Communication":
        dict_["data"] = base64.standard_b64decode(dict_["data"])
        return cls(**dict_)


class CommunicationsFaker(Exception):
    """Error in the communications faker"""


class CommunicationsCollectingSerial:
    """A communications collection pyserial.Serial

    Args:
        args: args for pyserial.Serial
        kwargs: kwargs for pyserial.Serial

    """

    def __init__(self, *args, **kwargs):
        self._serial = Serial(*args, **kwargs)
        self._collected_coms = []

    def read(self, size: int = 1) -> bytes:
        """Read `size` bytes"""
        data = self._serial.read(size)
        self._collected_coms.append(_Communication("READ", data))
        return data

    def write(self, data: bytes) -> None:
        """Write `data`"""
        self._serial.write(data)
        self._collected_coms.append(_Communication("WRITE", data))

    def __getattr__(self, name):
        """Return attribute from wrapped pyserial.Serial"""
        return getattr(self._serial, name)

    def reset_collected_coms(self) -> None:
        """Reset the collected communications"""
        self._collected_coms = []

    def save_collected_coms(self, path: Path) -> None:
        """Save the collected communications

        Args:
            path (Path): The path of the file to save to

        """
        collected_coms_as_json = [c.as_json() for c in self._collected_coms]
        with open(path, "w") as file_:
            dump(collected_coms_as_json, file_, indent=4)

    def close(self) -> None:
        """Close the underlying serial object"""
        self._serial.close()


class CommunicationsReplayingSerial:
    """A pyserial.Serial faker replaying collected data"""

    def __init__(self, *args, **kwargs):
        self._collected_coms: list[_Communication] | None = None

    def load_collected_coms(self, path) -> None:
        with open(path) as file_:
            collected_coms_as_jsonable = load(file_)
        self._collected_coms = [_Communication.from_json(j) for j in collected_coms_as_jsonable]

    def write(self, data) -> None:
        try:
            _com = self._collected_coms.pop(0)
        except IndexError:
            raise CommunicationsFaker("No more communications fragments")

        assert _com.type == "WRITE", "Was expecting write at this point"
        assert _com.data == data, "Incorrect data to be written"

    def read(self, size: int = 1) -> bytes:
        if size == 0 and (not self._collected_coms or self._collected_coms[0].type == "WRITE"):
            return b""

        try:
            _com = self._collected_coms.pop(0)
        except IndexError:
            raise CommunicationsFaker("No more communications fragments")

        if _com.type == "WRITE":
            raise CommunicationsFaker("Was expecting write")

        assert size == len(_com.data), "Incorrect data size"
        return _com.data

    @property
    def in_waiting(self) -> int:
        try:
            _com = self._collected_coms[0]
        except IndexError:
            return 0

        if _com.type == "WRITE":
            return 0
        else:
            return len(_com.data)

    def flush(self):
        ...
