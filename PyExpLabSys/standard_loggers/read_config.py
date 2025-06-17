import socket
import tomllib
import pathlib

def read_configuration(filename):
    host = socket.gethostname()
    home = pathlib.Path.home() / 'machines' / host
    with open(home / filename, 'rb') as f:
        config = tomllib.load(f)
    return config
