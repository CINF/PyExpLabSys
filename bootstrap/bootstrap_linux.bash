#!/bin/bash

# This script is used to setup a linux box for use with PyExpLabSys

##############################################################
# EDIT POINT START: Edit here to change what the script does #
##############################################################

# apt install packages line 1, general packages
#
# NOTE: python3 is not installed on lite raspbian image by default!!
apt1="openssh-server emacs graphviz screen ntp python python3 i2c-tools vim-nox"

# apt install packages line 2, python extensions
#
# NOTE: This line used to contain colorama, but it is a dependency of
# pip, so it will be installed anyway
apt2="python-pip python-mysqldb python3-pip python-numpy python3-numpy"

# apt install packages that has possibly changed name, written in list form and installed one at at time
declare -a apt3=("libpython2.7-dev" "libpython3-dev" "python-dev" "python3-dev" "libmysqlclient-dev" "libmariadbclient-dev")

# packages to be installe by pip
pippackages="minimalmodbus==0.6 pyusb python-usbtmc pyserial pyyaml pylint chainmap"
pip3packages="minimalmodbus==0.6 pyusb python-usbtmc pyserial pyyaml mysqlclient"
# Put packages into this array, whose installation sometimes fail
declare -a pip3problempackages=("pylint")

# These lines will be added to the ~/.bashrc file, to modify the PATH and
# PYTHONPATH for PyExpLabSys usage
bashrc_addition='
export PATH=$PATH:$HOME/PyExpLabSys/bin:$HOME/.local/bin
export PYTHONPATH=$HOME/PyExpLabSys
stty -ixon

machine_dir=$HOME/PyExpLabSys/machines/$HOSTNAME
if [ -d $machin_dir ]; then
    echo "Entering machine dir: $machine_dir"
    cd $machine_dir
fi
pistatus.py
'

# These lines will be added to ~/.bash_aliases
bash_aliases="
alias sagi=\"sudo apt-get install\"
alias sagr=\"sudo apt-get remove\"
alias acs=\"apt-cache search\"
alias sagu=\"sudo apt-get update\"
alias sagup=\"sudo apt-get upgrade\"
alias sagdu=\"sudo apt-get dist-upgrade\"
alias ll=\"ls -lh\"
alias df=\"df -h\"
alias emacs-nolint=\"emacs -q --load ~/PyExpLabSys/bootstrap/.emacs-simple\"
alias python=\"/usr/bin/python3\"

alias a=\"cd ~/PyExpLabSys/PyExpLabSys/apps\"
alias c=\"cd ~/PyExpLabSys/PyExpLabSys/common\"
alias d=\"cd ~/PyExpLabSys/PyExpLabSys/drivers\"
alias m=\"if [ -d ~/PyExpLabSys/machines/\$HOSTNAME ];then cd ~/PyExpLabSys/machines/\$HOSTNAME; else cd ~/PyExpLabSys/machines; fi\"
alias p=\"cd ~/PyExpLabSys/PyExpLabSys\"
alias b=\"cd ~/PyExpLabSys/bootstrap\"
alias s=\"screen -x\"
"

# Usage string, edit if adding another section to the script
usage="This is the CINF Linux bootstrap script

    USAGE: bootstrap_linux.bash SECTION

Where SECTION is the part of the bootstrap script that you want to run, lised below. If the value of \"all\" is given all section will be run. NOTE you can only supply one argument:

Sections:
bash        Edit PATH and PYTHONPATH in .bashrc to make PyExpLabSys scripts
            runnable and PyExpLabSys importable. Plus add bash aliasses for
            most common commands including apt commands.
git         Add common git aliases
install     Install commonly used packages e.g openssh-server
pip         Install extra Python packages with pip
autostart   Setup autostart cronjob
settings    Link in the PyExpLabSys settings file
pycheckers  Install Python code style checkers and hook them up to emacs and
            geany (if geany is already installed)

all         All of the above

doc         Install extra packages needed for writing docs (NOT part of all)
wiringpi    Install wiring pi and python-wiringpi
abelec      Setup device to use daq-modules from AB Electronics (NOT part of all)
dash        Install packages for dash
qt          Setup GUI environment: Qt and Qwt (for plots)
"
##################
# EDIT POINT END #
##################

# Functions
echobad(){
    echo -e "\033[1m\E[31m$@\033[0m"
}

echobold(){
    echo -e "\033[1m$@\033[0m"
}

echogood(){
    echo -e "\033[1m\E[32m$@\033[0m"
}

echoblue(){
    echo -e "\033[1m\E[34m$@\033[0m"
}

echoyellow(){
    echo -e "\033[1m\E[33m$@\033[0m"
}

# Defaults
reset_bash="NO"

# Checks argument number and if needed print usage
if [ $# -eq 0 ] || [ $# -gt 1 ];then
    echo "$usage"
    exit
fi

# Bash section
if [ $1 == "bash" ] || [ $1 == "all" ];then
    echo
    echobold "===> SETTING UP BASH"
    grep PATH ~/.bashrc > /dev/null
    if [ $? -eq 0 ];then
	echogood "---> .bashrc. previously setup"
	grep ".local.bin" ~/.bashrc > /dev/null
	if [ $? -eq 0 ];then
	    echogood "---> no update to PATH required"
	else
	    sed -i -e 's/.*PATH.*//g' $HOME/.bashrc
	    echo "$bashrc_addition" >> ~/.bashrc
	    echobad "---> Replacing old PATH setting with new one"
	fi

	# the stty setting was added later, check whether it is there
	# and otherwise add it
	grep "stty" ~/.bashrc > /dev/null
	if [ $? -ne 0 ];then
	    echo "stty -ixon" >> ~/.bashrc
	    echogood "---> .bashrc missed 'stty -ixon line', added it"
	fi

	# Change dir and pistatus was added later, check whether it is
	# there and otherwise add it
	grep "pistatus" ~/.bashrc > /dev/null
	if [ $? -ne 0 ];then
	    echo 'machine_dir=$HOME/PyExpLabSys/machines/$HOSTNAME' >> ~/.bashrc
	    echo 'if [ -d $machin_dir ]; then' >> ~/.bashrc
	    echo '    echo "Entering machine dir: $machine_dir"' >> ~/.bashrc
	    echo '    cd $machine_dir' >> ~/.bashrc
	    echo 'fi' >> ~/.bashrc
	    echo 'pistatus.py' >> ~/.bashrc
	    echogood "---> .bashrc missed change dir and pistatus, added it"
	fi
    else
	echoblue "---> Modifying .bashrc includes PATH and PYTHONPATH setup"
	echoblue "----> Making the following addition to .bashrc ============="
	echoyellow "$bashrc_addition"
	echoblue "----> ======================================================"
	echo "$bashrc_addition" >> ~/.bashrc
    fi

    echoblue "---> Writing bash aliasses to .bash_aliases"
    echoblue "----> Overwriting .bashrc_aliases with the following ======="
    echoyellow "$bash_aliases"
    echoblue "----> ======================================================"
    echo "$bash_aliases" > ~/.bash_aliases
    reset_bash="YES"
    echogood "+++++> DONE"
fi

# Git section
if [ $1 == "git" ] || [ $1 == "all" ];then
    echo
    echobold "===> SETTING UP GIT"
    echoblue "---> Setting up git aliases"
    echoblue "----> ci='commit -v'"
    git config --global alias.ci 'commit -v'
    echoblue "----> pr='pull --rebase'"
    git config --global alias.pr 'pull --rebase'
    echoblue "----> lol='log --graph --decorate --pretty=oneline --abbrev-commit'"
    git config --global alias.lol 'log --graph --decorate --pretty=oneline --abbrev-commit'
    echoblue "----> ba='branch -a'"
    git config --global alias.ba 'branch -a'
    echoblue "----> st='status'"
    git config --global alias.st 'status'
    echoblue "----> cm='commit -m'"
    git config --global alias.cm 'commit -m'
    echoblue "---> Make git use colors"
    git config --global color.ui true
    echoblue "---> Set default push setting"
    git config --global push.default matching
    echogood "+++++> DONE"
fi

# Install packages
if [ $1 == "install" ] || [ $1 == "all" ];then
    echo
    echobold "===> INSTALLING PACKAGES"
    echoblue "---> Updating package archive information"

    # Update, but only if it has not just been done (within the last
    # 10 hours), since it actually takes a while on a RPi.
    #
    # NOTE. The method is based on checking the last modification of
    # the apt cache file, which may not the perfect method, we will
    # test it and see
    last_update=`stat /var/cache/apt/pkgcache.bin --format="%Y"`
    now=`date +%s`
    since_last_update=$((now-last_update))
    if [ $since_last_update -gt 36000 ];then
	sudo apt-get update
    else
	echoblue "Skipping, since it was done" $(($since_last_update/3600)) "hours ago"
    fi

    aptgetprefix='sudo apt-get -y'

    echoblue "---> Upgrade all existing packages"
    $aptgetprefix dist-upgrade
    echoblue "---> Installing packages"
    echoblue "----> Install: $apt1"
    $aptgetprefix install $apt1
    echoblue "----> Install: $apt2"
    $aptgetprefix install $apt2

    # Install package individually, that may have changed name
    for package in "${apt3[@]}";do
	echoblue "----> Attempting to install \"$package\" as an individual package"
	$aptgetprefix install $package
    done

    echoblue "---> Remove un-needed packages, if any"
    $aptgetprefix autoremove
    echoblue "---> Clear apt cache"
    $aptgetprefix clean

    echoblue "---> Enable ssh by creating /boot/ssh"
    sudo touch /boot/ssh
    echogood "+++++> DONE"
fi

# Install extra packages with pip
if [ $1 == "pip" ] || [ $1 == "all" ];then
    echo
    # Test if pip is there
    pip --version > /dev/null
    if [ $? -eq 0 ];then
	echobold "===> INSTALLING EXTRA PYTHON PACKAGES WITH PIP"
	echoblue "---> $pippackages"
	sudo pip install -U $pippackages
	echogood "+++++> DONE"
    else
	echobad "pip not installed, run install step and then re-try pip step"
    fi

    echo


    # Test if pip3 is there
    PIPEXECUTABLE=`which pip3`
    if [ $? -ne 0 ];then
	PIPEXECUTABLE=`which pip-3.2`
    fi

    if [ $? -eq 0 ];then
	echobold "===> INSTALLING EXTRA PYTHON PACKAGES WITH PIP3"
	echoblue "---> Installing: $pip3packages"
	sudo $PIPEXECUTABLE install -U $pip3packages
	# Individual packages
	for package in "${pip3problempackages[@]}";do
	    echoblue "---> Installing \"$package\" as an invididual package"
	    sudo $PIPEXECUTABLE install -U $package
	done
	echogood "+++++> DONE"
    else
	echobad "pip3 not installed, run install step and then re-try pip step"
    fi
fi

# Setup autostart cronjob
if [ $1 == "autostart" ] || [ $1 == "all" ];then
    echo
    echobold "===> SETTINGS UP AUTOSTART CRONJOB"

    # Form path of autostart script
    thisdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    pelsdir=`dirname $thisdir`
    autostartpath=$pelsdir"/bin/autostart.py"
    cronline="@reboot SHELL=/bin/bash BASH_ENV=$HOME/.bashrc \
/usr/bin/env python $autostartpath 2>&1 | \
/usr/bin/logger -t cinfautostart"

    echoblue "Using autostart path: $autostartpath"

    # Check if there has been installed cronjobs before
    crontab -l > /dev/null
    if [ $? -eq 0 ];then
        crontab -l | grep $autostartpath > /dev/null
        if [ $? -eq 0 ];then
            echoblue "Autostart cronjob already installed"
        else
            crontab -l | { cat; echo $cronline; } | crontab -
            echoblue "Installed autostart cronjob"
        fi
    else
        cronlines="# Output of the crontab jobs (including errors) is sent through\n\
# email to the user the crontab file belongs to (unless redirected).\n\
#\n\
# For example, you can run a backup of all your user accounts\n\
# at 5 a.m every week with: # 0 5 1 tar -zcf /var/backups/home.tgz /home/\n\
#\n\
# For more information see the manual pages of crontab(5) and cron(8)\n\
#\n\
# m h dom mon dow command\n\
$cronline"
        crontab -l | { cat; echo -e $cronlines; } | crontab -
        echoblue "Had no cronjobs. Installed with standard header."
    fi
    echogood "+++++> DONE"
fi


# Setup autostart cronjob
if [ $1 == "settings" ] || [ $1 == "all" ];then
    echobold "===> LINKING PYEXPLABSYS SETTINGS FILE IN PLACE"
    if [ -f ~/.config/PyExpLabSys/user_settings.yaml ];then
        echogood "Settings file already linked in"
    else
        echoblue "---> Make ~/.config/PyExpLabSys dir"
        mkdir -p ~/.config/PyExpLabSys
        echoblue "---> Link settings into dir:"
        echoblue "---> ~/PyExpLabSys/bootstrap/user_settings.yaml into ~/.config/PyExpLabSys/"
        ln -s ~/PyExpLabSys/bootstrap/user_settings.yaml ~/.config/PyExpLabSys/user_settings.yaml
    fi
    echogood "+++++> DONE"
fi


if [ $1 == "pycheckers" ] || [ $1 == "all" ];then
    echobold "===> SETTINGS UP CODE STYLE CHECKERS FOR EMACS AND GEANY"
    echoblue "---> Make ~/.emacs.d/lisp dir"
    mkdir -p ~/.emacs.d/lisp
    echoblue "---> Copy flymake-cursor.el to ~/.emacs.d/lisp dir"
    cp ~/PyExpLabSys/bootstrap/flymake-cursor.el ~/.emacs.d/lisp/
    echoblue "---> Copy .emacs to ~/.emacs.d/lisp dir"
    cp ~/PyExpLabSys/bootstrap/.emacs ~/
    echoblue "---> Copy .pylintrc to ~/ dir"
    cp ~/PyExpLabSys/bootstrap/.pylintrc ~/
    # Hook geany up with pychecker, but only if geany is already installed
    if [ -d  ~/.config/geany/filedefs ]; then
	echoblue "---> Copy geany filedefs (actions for files) to ~/.config/geany/filedefs"
	cp ~/PyExpLabSys/bootstrap/filetypes.common ~/.config/geany/filedefs/
	cp ~/PyExpLabSys/bootstrap/filetypes.python ~/.config/geany/filedefs/
    else
	echobad "pycheckers configuration for geany NOT installed. First install "
	echobad "geany and then rerun pycheckers step"
    fi
    echogood "+++++> DONE"
fi

# Install extra packages needed for writing docs
if [ $1 == "docs" ];then
    # TODO add sphinx and extra package needed to dependency graph
    echobold "===> INSTALLING EXTRA PACKAGES FOR WRITING DOCS"
    echo

    # Sphinx and graphviz
    echoblue "---> Installing python-sphinx and graphviz with apt-get"
    sudo apt-get install python-sphinx graphviz

    # sphinxcontrib-napoleon, test if pip is there
    pip --version > /dev/null
    if [ $? -eq 0 ];then
	echoblue "---> Installing sphinxcontrib-napoleon with pip"
	sudo pip install -U sphinxcontrib-napoleon
    else
	echobad "pip not installed, run install step and then re-try this step"
    fi

    echogood "+++++> DONE"
fi

if [ $1 == "wiringpi" ];then
    echobold "===> INSTALLING WIRINGPI"
    echoblue "---> Installing wiringpi with apt-get"
    sudo apt-get install wiringpi
    echoblue "---> Installing python wiringpi with pip (as root)"
    sudo pip2 install wiringpi
    sudo pip3 install wiringpi
    echoblue "---> Setting sticky bit on python2 and python3"
    sudo chmod +s `which python2`
    sudo chmod +s `which python3`
    echogood "+++++> DONE"
fi

if [ $1 == "abelec" ];then
    # TODO: Improve script to allow multiple executions
    echobold "===> INSTALLING EXTRA PACKAGES FOR AB ELECTRONICS"
    sudo apt-get install i2c-tools python-smbus
    echo

    sudo touch /etc/modprobe.d/raspi-blacklist.conf # Make sure file is there before removing
    sudo rm /etc/modprobe.d/raspi-blacklist.conf
    echogood "Removed raspi-blacklist"
    cd ~/
    
    export ABDIR=$HOME/ABElectronics_Python_Libraries/
    if [ ! -d "$ABDIR" ]; then
	git clone https://github.com/abelectronicsuk/ABElectronics_Python_Libraries.git
	echogood "Cloned git reposetory"
    else
        cd "$ABDIR"
	git pull
	echogood "Updated git repository"
    fi

    if [ -d ~/ABElectronics_Python_Libraries/ABElectronics_DeltaSigmaPi/ ]; then
	echogood "~/ABElectronics_Python_Libraries/ABElectronics_DeltaSigmaPi/ found, adding to PYHONPATH"
	bashrc_addition="export PYTHONPATH=\${PYTHONPATH}:~/ABElectronics_Python_Libraries/ABElectronics_DeltaSigmaPi/"
    else
	echogood "~/ABElectronics_Python_Libraries/ABElectronics_DeltaSigmaPi/ NOT found, adding ~/ABElectronics_Python_Libraries/ to PYHONPATH"
	bashrc_addition="export PYTHONPATH=\${PYTHONPATH}:~/ABElectronics_Python_Libraries/"
    fi

    echo ${PYTHONPATH}
    grep ABElectronics ~/.bashrc > /dev/null
    if [ $? -eq 0 ];then
	echobad "---> PATH already setup in .bashrc. NO MODIFICATION IS MADE"
    else
	echo "$bashrc_addition" >> ~/.bashrc
	echogood "Added reposetory to python path"
    fi

    grep i2c-dev /etc/modules > /dev/null
    if [ $? -eq 0 ];then
	echobad "---> i2c-dev already added to modules"
    else
	sudo sh -c 'echo "i2c-dev" >> /etc/modules'
	echogood "Added spi-dev to auto-loaded modules"
    fi

    echogood "Adding user to spi and i2c groups"
    sudo usermod -a -G spi pi
    sudo usermod -a -G i2c pi

    echobad "ON NEWER RASPBERRY PI'S REMEMBER TO ENABLE SPI WITH raspi-config"

    echogood "+++++> DONE"
fi


if [ $1 == "dash" ];then
    # TODO: Improve script to allow multiple executions
    echobold "===> INSTALLING EXTRA PACKAGES FOR DASH"
    pip3 install dash==0.28.5  # The core dash backend
    pip3 install dash-html-components==0.13.2  # HTML components
    pip3 install dash-core-components==0.35.1  # Supercharged components
    echo
    echogood "+++++> DONE"
fi

# GUI section (Qt and Qwt)
if [ $1 == "qt" ];then
    echobold "===> INSTALLING EXTRA PACKAGES FOR GUIS"
    echo

    # qt and pyqwt
    echoblue "---> Installing python-qt4 and python-qwt5-qt4 with apt-get"
    sudo apt-get install python-qt4 python-qwt5-qt4

    echogood "+++++> DONE"
fi

# Print message about resetting bash after bash modifications
if [ $reset_bash == "YES" ];then
    echo
    echobold "##> NOTE! ~/PyExpLabSys/bin has been added to PATH, which means"
    echobold "##> that the user specific rgit, kgit and agit commands for "
    echobold "##> Robert, Kenneth and Anders can be used."
    echobold "##>"
    echobold "##> NOTE! Your bash environment has been modified."
    echobold "##> Run: \"source ~/.bashrc\" to make the changes take effect."
fi
