#!/usr/bin/env python2
# pylint: disable=invalid-name,global-statement

"""This script is used to setup a linux box for use with PyExpLabSys"""

from __future__ import print_function

from functools import partial
from os.path import join, expanduser
import argparse
import subprocess
import logging


##############################################################
# EDIT POINT START: Edit here to change what the script does #
##############################################################

# apt install packages line 1, general packages
#
# NOTE: python3 is not installed on lite raspbian image by default!!
APT1 = "openssh-server emacs graphviz screen ntp libmysqlclient-dev python python3"

# apt install packages line 2, python extensions
#
# NOTE: This line used to contain colorama, but it is a dependency of
# pip, so it will be installed anyway
APT2 = "python-pip python-mysqldb python3-pip"

# packages to be installe by pip
PIPPACKAGES = "minimalmodbus pyusb python-usbtmc pyserial"
PIP3PACKAGES = "minimalmodbus pyusb python-usbtmc pyserial mysqlclient pylint"

# These lines will be added to the ~/.bashrc file, to modify the PATH and
# PYTHONPATH for PyExpLabSys usage
BASHRC_ADDITION = """
export PATH=$PATH:$HOME/PyExpLabSys/bin
export PYTHONPATH=$HOME/PyExpLabSys
"""

# These lines will be added to ~/.bash_aliases
BASH_ALIASES = """
alias sagi=\"sudo apt-get install\"
alias sagr=\"sudo apt-get remove\"
alias acs=\"apt-cache search\"
alias sagu=\"sudo apt-get update\"
alias sagup=\"sudo apt-get upgrade\"
alias sagdu=\"sudo apt-get dist-upgrade\"
alias ll=\"ls -lh\"
alias df=\"df -h\"
alias emacs-nolint=\"emacs -q --load ~/PyExpLabSys/bootstrap/.emacs-simple\"
"""

# Usage string, edit if adding another section to the script
USAGE = """This is the CINF Linux bootstrap script

Sections:

bash        Edit PATH and PYTHONPATH in .bashrc to make PyExpLabSys scripts
            runnable and PyExpLabSys importable. Plus add bash aliasses for
            most common commands including apt commands.
git         Add common git aliases
install     Install commonly used packages e.g openssh-server
pip         Install extra Python packages with pip
autostart   Setup autostart cronjob
pycheckers  Install Python code style checkers and hook them up to emacs and
            geany (if geany is already installed)

all         All of the above

doc         Install extra packages needed for writing docs (NOT part of all)
abelec      Setup device to use daq-modules from AB Electronics (NOT part of all)
qt          Setup GUI environment: Qt and Qwt (for plots, NOT part of all)
""".strip()

ALL = ['bash', 'git', 'install', 'pip', 'autostart', 'pycheckers']

ALL_AVAILABLE_SECTIONS = {
    'bash', 'git', 'install', 'pip', 'autostart', 'pycheckers',
    'doc', 'abelec', 'qt',
}

###################
## EDIT POINT END #
###################

### Setup logging
logging.basicConfig(
    filename=join(expanduser('~'), 'bootstrap_log'),
    filemode='w',
    format='%(asctime)s: %(message)s',
    #datefmt='',
    level=logging.DEBUG,
)
my_formatter = logging.Formatter('%(asctime)s: %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(my_formatter)
logging.getLogger('').addHandler(stream_handler)
logging.debug('Use less -R to see the log with colors')


### Functions
def echo(text='', color=None):
    """Print with ansi color"""
    for line in text.split('\n'):
        if color:
            line = '\x1b[{}m{}\x1b[0m'.format(color, line)
        logging.debug(line)


# Coloring and logging
echobad = partial(echo, color='1;31')
echobold = partial(echo, color='1;37')
echogood = partial(echo, color='1;32')
echoblue = partial(echo, color='1;34')
echoyellow = partial(echo, color='1;33')

# Command line calls
check_call = partial(subprocess.check_output, shell=True)
call = partial(subprocess.call, shell=True)


### Defaults
RESET_BASH = False


def logged_call(command):
    """Run a command at the command line and log the output"""
    process = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE)
    while True:
        line = process.stdout.readline()
        if line:
            logging.debug("| " + line.strip('\n'))
        else:
            break

# Section functions

def test():
    """Test function"""
    logged_call("python output.py")


def bash():
    """bash section"""
    echo()
    echobold("===> SETTING UP BASH")

    try:
        # Check if PATH is already in .bashrc and in that case do nothing
        check_call('grep PATH ~/.bashrc > /dev/null')
        echobad("---> PATH already setup in .bashrc. NO MODIFICATION IS MADE")
        status = [('Setup PATH', 'OK, already done')]
    except subprocess.CalledProcessError:
        echoblue("---> Modifying PATH and adding PYTHONPATH by editing .bashrc")
        echoblue("----> Making the following addition to .bashrc =============")
        echoyellow(BASHRC_ADDITION)
        echoblue("----> ======================================================")
        with open(join(expanduser('~'), '.bashrc'), 'a') as file_:
            file_.write(BASHRC_ADDITION)
        status = [('Setup PATH', 'OK')]

    echoblue("---> Writing bash aliasses to .bash_aliases")
    echoblue("----> Overwriting .bashrc_aliases with the following =======")
    echoyellow(BASH_ALIASES)
    echoblue("----> ======================================================")
    with open(join(expanduser('~'), '.bash_aliases'), 'w') as file_:
        file_.write(BASH_ALIASES)
    status.append(('Setup bash aliases', 'OK'))

    # bash shoud be restarted after this
    global RESET_BASH
    RESET_BASH = True

    echogood("+++++> DONE")
    return status


def git():
    """git section"""
    echo('')
    echobold("===> SETTING UP GIT")
    echoblue("---> Setting up git aliases")
    return_code_sum = 0
    aliases = (
        ('ci', 'commit -v'),
        ('pr', 'pull --rebase'),
        ('lol', 'log --graph --decorate --pretty=oneline --abbrev-commit'),
        ('ba', 'branch -a'),
        ('st', 'status'),
        ('cm', 'commit -m'),
    )
    for alias, full_command in aliases:
        echoblue("{}={}".format(alias, full_command))
        return_code_sum += call("git config --global alias.{} '{}'"\
                                .format(alias, full_command))
    if return_code_sum > 0:
        status = [('git aliases', 'FAILED on {} aliases'.format(return_code_sum))]
    else:
        status = [('git aliases', 'OK')]
        
    echoblue("---> Make git use colors")
    if call("git config --global color.ui true") == 0:
        status.append(('setup git color', 'OK'))
    else:
        status.append(('setup git color', 'FAILED'))
    echogood("+++++> DONE")

    return status



## Install packages
#if [ $1 == "install" ] || [ $1 == "all" ];then
#    echo 
#    echobold "===> INSTALLING PACKAGES"
#    echoblue "---> Updating package archive information"
#
#    # Update, but only if it has not just been done (within the last
#    # 10 hours), since it actually takes a while on a RPi.
#    #
#    # NOTE. The method is based on checking the last modification of
#    # the apt cache file, which may not the perfect method, we will
#    # test it and see
#    last_update=`stat /var/cache/apt/pkgcache.bin --format="%Y"`
#    now=`date +%s`
#    since_last_update=$((now-last_update))
#    if [ $since_last_update -gt 36000 ];then
#	sudo apt-get update
#    else
#	echoblue "Skipping, since it was done" $(($since_last_update/3600)) "hours ago"
#    fi
#
#    echoblue "---> Upgrade all existing packages"
#    sudo apt-get -y dist-upgrade
#    echoblue "---> Installing packages"
#    echoblue "----> Install: $apt1"
#    sudo apt-get -y install $apt1
#    echoblue "----> Install: $apt2"
#    sudo apt-get -y install $apt2
#    echoblue "---> Remove un-needed packages, if any"
#    sudo apt-get -y autoremove
#    echoblue "---> Clear apt cache"
#    sudo apt-get clean
#    echogood "+++++> DONE"
#fi
#
## Install extra packages with pip
#if [ $1 == "pip" ] || [ $1 == "all" ];then
#    echo
#    # Test if pip is there
#    pip --version > /dev/null
#    if [ $? -eq 0 ];then
#	echobold "===> INSTALLING EXTRA PYTHON PACKAGES WITH PIP"
#	echoblue "---> $pippackages"
#	sudo pip install -U $pippackages
#	echogood "+++++> DONE"
#    else
#	echobad "pip not installed, run install step and then re-try pip step"
#    fi
#
#    echo
#    # Test if pip3 is there
#    pip3 --version > /dev/null
#    if [ $? -eq 0 ];then
#	echobold "===> INSTALLING EXTRA PYTHON PACKAGES WITH PIP3"
#	echoblue "---> $pip3packages"
#	sudo pip3 install -U $pip3packages
#	echogood "+++++> DONE"
#    else
#	echobad "pip3 not installed, run install step and then re-try pip step"
#    fi
#fi
#
## Setup autostart cronjob
#if [ $1 == "autostart" ] || [ $1 == "all" ];then
#    echo
#    echobold "===> SETTINGS UP AUTOSTART CRONJOB"
#
#    # Form path of autostart script
#    thisdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#    pelsdir=`dirname $thisdir`
#    autostartpath=$pelsdir"/bin/autostart.py"
#    cronline="@reboot SHELL=/bin/bash BASH_ENV=$HOME/.bashrc \
#/usr/bin/env python $autostartpath 2>&1 | \
#/usr/bin/logger -t cinfautostart"
#
#    echoblue "Using autostart path: $autostartpath"
#
#    # Check if there has been installed cronjobs before
#    crontab -l > /dev/null
#    if [ $? -eq 0 ];then
#        crontab -l | grep $autostartpath > /dev/null
#        if [ $? -eq 0 ];then
#            echoblue "Autostart cronjob already installed"
#        else
#            crontab -l | { cat; echo $cronline; } | crontab -
#            echoblue "Installed autostart cronjob"
#        fi
#    else
#        cronlines="# Output of the crontab jobs (including errors) is sent through\n\
## email to the user the crontab file belongs to (unless redirected).\n\
##\n\
## For example, you can run a backup of all your user accounts\n\
## at 5 a.m every week with: # 0 5 1 tar -zcf /var/backups/home.tgz /home/\n\
##\n\
## For more information see the manual pages of crontab(5) and cron(8)\n\
##\n\
## m h dom mon dow command\n\
#$cronline"
#        crontab -l | { cat; echo -e $cronlines; } | crontab -
#        echoblue "Had no cronjobs. Installed with standard header."
#    fi
#    echogood "+++++> DONE"
#fi
#
#
#if [ $1 == "pycheckers" ] || [ $1 == "all" ];then
#    echobold "===> SETTINGS UP CODE STYLE CHECKERS FOR EMACS AND GEANY"
#    echoblue "---> Make ~/.emacs.d/lisp dir"
#    mkdir -p ~/.emacs.d/lisp
#    echoblue "---> Copy flymake-cursor.el to ~/.emacs.d/lisp dir"
#    cp ~/PyExpLabSys/bootstrap/flymake-cursor.el ~/.emacs.d/lisp/
#    echoblue "---> Copy .emacs to ~/.emacs.d/lisp dir"
#    cp ~/PyExpLabSys/bootstrap/.emacs ~/
#    echoblue "---> Copy .pylintrc to ~/ dir"
#    cp ~/PyExpLabSys/bootstrap/.pylintrc ~/
#    # Hook geany up with pychecker, but only if geany is already installed
#    if [ -d  ~/.config/geany/filedefs ]; then
#	echoblue "---> Copy geany filedefs (actions for files) to ~/.config/geany/filedefs"
#	cp ~/PyExpLabSys/bootstrap/filetypes.common ~/.config/geany/filedefs/
#	cp ~/PyExpLabSys/bootstrap/filetypes.python ~/.config/geany/filedefs/
#    else
#	echobad "pycheckers configuration for geany NOT installed. First install "
#	echobad "geany and then rerun pycheckers step"
#    fi
#    echogood "+++++> DONE"
#fi
#
## Install extra packages needed for writing docs
#if [ $1 == "docs" ];then
#    # TODO add sphinx and extra package needed to dependency graph
#    echobold "===> INSTALLING EXTRA PACKAGES FOR WRITING DOCS"
#    echo
#
#    # Sphinx and graphviz
#    echoblue "---> Installing python-sphinx and graphviz with apt-get"
#    sudo apt-get install python-sphinx graphviz
#
#    # sphinxcontrib-napoleon, test if pip is there
#    pip --version > /dev/null
#    if [ $? -eq 0 ];then
#	echoblue "---> Installing sphinxcontrib-napoleon with pip"
#	sudo pip install -U sphinxcontrib-napoleon
#    else
#	echobad "pip not installed, run install step and then re-try this step"
#    fi
#
#    echogood "+++++> DONE"
#fi
#
#if [ $1 == "abelec" ];then
#    # TODO: Improve script to allow multiple executions
#    echobold "===> INSTALLING EXTRA PACKAGES FOR AB ELECTRONICS"
#    sudo apt-get install i2c-tools python-smbus
#    echo
#
#    sudo touch /etc/modprobe.d/raspi-blacklist.conf # Make sure file is there before removing
#    sudo rm /etc/modprobe.d/raspi-blacklist.conf
#    echogood "Removed raspi-blacklist"
#    cd ~/
#    
#    export ABDIR=$HOME/ABElectronics_Python_Libraries/
#    if [ ! -d "$ABDIR" ]; then
#	git clone https://github.com/abelectronicsuk/ABElectronics_Python_Libraries.git
#	echogood "Cloned git reposetory"
#    else
#        cd "$ABDIR"
#	git pull
#	echogood "Updated git repository"
#    fi
#
#    echo ${PYTHONPATH}
#    bashrc_addition="export PYTHONPATH=\${PYTHONPATH}:~/ABElectronics_Python_Libraries/ABElectronics_DeltaSigmaPi/"
#    grep SigmaPi ~/.bashrc > /dev/null
#    if [ $? -eq 0 ];then
#	echobad "---> PATH already setup in .bashrc. NO MODIFICATION IS MADE"
#    else
#	echo "$bashrc_addition" >> ~/.bashrc
#	echogood "Added reposetory to python path"
#    fi
#
#    grep i2c-dev /etc/modules > /dev/null
#    if [ $? -eq 0 ];then
#	echobad "---> i2c-dev already added to modules"
#    else
#	sudo sh -c 'echo "i2c-dev" >> /etc/modules'
#	echogood "Added spi-dev to auto-loaded modules"
#    fi
#
#    echogood "Adding user to spi and i2c groups"
#    sudo usermod -a -G spi pi
#    sudo usermod -a -G i2c pi
#
#    echogood "+++++> DONE"
#fi
#
## GUI section (Qt and Qwt)
#if [ $1 == "qt" ];then
#    echobold "===> INSTALLING EXTRA PACKAGES FOR GUIS"
#    echo
#
#    # qt and pyqwt
#    echoblue "---> Installing python-qt4 and python-qwt5-qt4 with apt-get"
#    sudo apt-get install python-qt4 python-qwt5-qt4
#
#    echogood "+++++> DONE"
#fi
#
## Print message about resetting bash after bash modifications
#if [ $reset_bash == "YES" ];then
#    echo
#    echobold "##> NOTE! ~/PyExpLabSys/bin has been added to PATH, which means"
#    echobold "##> that the user specific rgit, kgit and agit commands (for "
#    echobold "##> Robert, Kenneth and Anders) can be used."
#    echobold "##>"
#    echobold "##> NOTE! Your bash environment has been modified."
#    echobold "##> Run: \"source ~/.bashrc\" to make the changes take effect."
#fi
#

def main():
    """Main function"""
    # Create command line argument parser
    parser = argparse.ArgumentParser(
        description=USAGE,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        'section', nargs="+",
        help='one or more sections to run, see possible values above',
    )
    args = parser.parse_args()

    # Form the list of sections to run
    sections = []
    for section in args.section:
        if section == 'all':
            sections += ALL
        else:
            sections.append(section)

    # Run the sections
    results = []
    for section in sections:
        if section not in ALL_AVAILABLE_SECTIONS:
            message = ('The sections "{}" is not the set of '
                       'ALL_AVAILABLE_SECTIONS'.format(section))
            logging.error('ERROR ' + message)
            raise RuntimeError(message)
        function = globals()[section]
        results.append((section, function()))

    # Print out a summary
    echo('\n######## SUMMARY ########')
    for section, section_results in results:
        echo()
        echo("SECTION: " + section)
        for section_result in section_results:
            echo("{:.<20} {}".format(*section_result))
    echo('\n######## SUMMARY END ####')

main()
