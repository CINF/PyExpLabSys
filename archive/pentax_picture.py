import os
from subprocess import call

def AcquireImage(filename):
    call(["pktriggercord-cli", "--model=k-r","--output_file=pentax"])
    os.rename("pentax-0000.jpg",filename)

if __name__ == "__main__":
    AcquireImage("test.jpg")
