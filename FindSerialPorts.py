import grp
import os


def find_ports():
    list = os.listdir('/dev')

    ports = []
    for file in list:
        f = os.stat('/dev/' + file)
        gid = f.st_gid
        group = grp.getgrgid(gid)[0]
        if group == 'dialout':
            if file not in ['ttyprintk']:
                ports.append(file)
    return ports
    
if __name__ == '__main__':
    print find_ports()
