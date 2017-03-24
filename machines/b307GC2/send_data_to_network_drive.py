#!/usr/bin/env python3

"""Script to one way synchronizes local data to ait drive"""

from __future__ import print_function

from os import listdir
import os.path as path
import sys
import argparse
import subprocess
import time

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)

# Python 3 check
if sys.version_info.major != 3:
    raise RuntimeError('Run using Python 3')

DATA_PATH = '/run/user/1000/gvfs/smb-share:domain=Workgroup,server=case-ec-gc-02,share=1,user=gc/'
NETWORK_DRIVE_PATH = '/home/surfcat/o/FYSIK/list-SurfCat/setups/307_GC2/active'
MOUNT_PATH = '/home/surfcat/o'
MOUNT_COMMAND = (
    'sudo mount.cifs //dtu-storage.win.dtu.dk/Department {mount_path} '
    '-o dom=win,username={{username}},uid=`id -u $USER`,gid=`id -g $USER`'
).format(mount_path=MOUNT_PATH)
UNMOUNT = 'sudo fusermount -u {}'.format(MOUNT_PATH)
RSYNC_COMMAND = 'rsync -rltOgoDv {} {}'.format(DATA_PATH, NETWORK_DRIVE_PATH)


def check_network_drive():
    """Check whether the network drive is mounted"""
    return path.isdir(NETWORK_DRIVE_PATH)


def mount_network_drive():
    """Mount the network drive"""
    # Get DTU initials
    # Try and mount drive
    # If not succeed, retry
    stop_trying = False
    while not stop_trying:
        print('### {:#<70}'.format('Mount network drive '))
        dtu_initials = input('Enter DTU initials of the user mounting\n'
                             'the network drive followed by (Enter): ')

        # Check that the username is valid
        try:
            dtu_initials.encode('ascii')
            is_ascii = True
        except UnicodeEncodeError:
            is_ascii = False

        if not (is_ascii and dtu_initials.isalpha()):
            print('Username may only contain letters a-z and A-Z')
            continue

        # Mount
        print('Using initials:', dtu_initials, end='\n\n')
        print('Attempting to mount network drive')
        mount_command = MOUNT_COMMAND.format(username=dtu_initials)
        return_code = subprocess.call(mount_command, shell=True)

        # Check if unsuccessful and retry
        if return_code != 0:
            print('Mount failed. Retry initials and retyr now of press Ctrl-C to abort')
            continue

        stop_trying = True


def virtual_machine_share_is_mounted():
    """Is the virtual machine share mounted"""
    try:
        content = listdir(DATA_PATH)
    except OSError:
        time.sleep(1)
    except:
        pass
    
    try:
        content = listdir(DATA_PATH)
    except FileNotFoundError:
        return False
        
    return len(content) > 4


def mount_virtual_machine_share():
    """Mount the folder shared onto the private network from the virtual machine"""
    # Should not be mounted
    if virtual_machine_share_is_mounted():
        print("Virtual machine share already mounted, unmounting")
        unmount_virtual_machine_share()
        time.sleep(3)
        
    subprocess.call("/home/surfcat/mount.expect")
    time.sleep(2)

    error_msg = ("!!!!!!!!!! FAILED !!!!!!!!!!\n\n"
                 "Failed to mount shared drive from the virtual "
                 "machine. Make the GC virtual machine is running\n\n"
                 "!!!!!!!!!! FAILED !!!!!!!!!!")

    if not virtual_machine_share_is_mounted():
        print(error_msg)
        raise SystemExit(1)


def unmount_virtual_machine_share():
    """Unmount above"""
    subprocess.call("gvfs-mount -u /run/user/1000/gvfs/smb-share:domain=Workgroup,server=case-ec-gc-02,share=1,user=gc/", shell=True)


def synchronize():
    """Synchronize new data to the AIT drive

    Use rsync to sync.

    The -a (archive) options, that one would normally use for this
    kind of task, doesn't quite fit due to the limitations of the
    samba share, but it is a good template.

    -a implies -rlptgoD and (no -H,-A,-X). The options mean:

     -r, --recursive             recurse into directories
     -l, --links                 copy symlinks as symlinks
     -p, --perms                 preserve permissions
     -t, --times                 preserve modification times
     -g, --group                 preserve group
     -o, --owner                 preserve owner (super-user only)
     -D                          same as --devices --specials

    NOT:

     -H, --hard-links            preserve hard links
     -A, --acls                  preserve ACLs (implies -p)
     -X, --xattrs                preserve extended attributes

    (These descriptions are copied from the rsync man page)

    We cannot use the options to preserve permissions, since it will
    not work and cause warnings (so no -p). We can preserve
    modification time stamp but only on files and not on directories
    (so -tO), where the -O means:

     -O, --omit-dir-times        omit directories from --times

    NOTE: We explicitely do not use -z since the files are copied
    between two local folders to sompression is pointless.

    We do NOT use --delete, so that files are preserved on the backup
    location even if they are deleted on the data location. This is a
    paranoid measure and may be changed in the future (since if we
    trust the versioning of the AIT system, we should also dare to
    delete files from the backup).

    Finally we ask fpr verbose output with -v

    So:
       rsync -rltOgoDv

    """
    print("Synchronize files with command:", RSYNC_COMMAND, sep="\n")
    print("\n### sync output start #################################################")
    return_code = subprocess.call(RSYNC_COMMAND, shell=True)
    print("### sync output end ###################################################\n")
    if return_code == 0:
        print("Synchronization completed SUCCESSFULLY!")
    else:
        print("The synchronization command reported and error. Please check the output "
              "to find the cause")



def main():
    """Main function

    Performs the following actions:

    1) Make sure the network drive is mounted
    1a) If not, suggest to mount it
    2) If mounted, synchronize data
    """

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Synchronize GC data with AIT drive.'
    )
    parser.add_argument('--unmount', '-u', action='store_true', default=False,
                        help='Unmount the AIT network drive')

    args = parser.parse_args()

    # Unmount if requested
    if args.unmount:
        subprocess.call(UNMOUNT, shell=True)
        return

    # Check if network drive
    if not check_network_drive():
        print('Network drive not mounted')
        mount_network_drive()
    else:
        print('Network drive already mounted')

    mount_virtual_machine_share()
    synchronize()
    unmount_virtual_machine_share()

start = time.time()
main()
print("Done. {:.1f} s".format(time.time() - start))
input("Press enter to exit")
