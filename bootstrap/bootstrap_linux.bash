#!/bin/bash

# This script is used to setup a linux box for use with PyExpLabSys

##############################################################
# EDIT POINT START: Edit here to change what the script does #
##############################################################

# apt install packages line 1, general packages
# NOTE pip is placed here, because right now it pulls in python2.6, which
# I prefer is complete before installing python packages
apt1="openssh-server emacs python-pip graphviz screen"

# apt install packages line 2, python extensions
apt2="python-mysqldb python-serial"

# apt install packages line 3, code checkers
apt3="pyflakes pylint"

# packages to be installe by pip
pippackages="minimalmodbus"

# These lines will be added to the ~/.bashrc file, to modify the PATH and
# PYTHONPATH for PyExpLabSys usage
bashrc_addition="
export PATH=$PATH:$HOME/PyExpLabSys/bin
export PYTHONPATH=$HOME/PyExpLabSys
"

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
pycheckers  Install Python code style checkers and hook them up to emacs and
            geany (if geany is already installed)

all         All of the above
doc         Install extra packages needed for writing docs (NOT part of all)
abelec      Setup device to use daq-modules from AB Electronics (NOT part of all)
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
	echobad "---> PATH already setup in .bashrc. NO MODIFICATION IS MADE"
    else
	echoblue "---> Modifying PATH and adding PYTHONPATH by editing .bashrc"
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
    echogood "+++++> DONE"
fi

# Install packages
if [ $1 == "install" ] || [ $1 == "all" ];then
    echo 
    echobold "===> INSTALLING PACKAGES"
    echoblue "---> Updating package archive information"
    sudo apt-get update
    echoblue "---> Upgrade all existing packages"
    sudo apt-get dist-upgrade
    echoblue "---> Installing packages"
    echoblue "----> Install: $apt1"
    sudo apt-get -y install $apt1
    echoblue "----> Install: $apt2"
    sudo apt-get -y install $apt2
    echoblue "----> Install: $apt3"
    sudo apt-get -y install $apt3
    echoblue "---> Remove un-needed packages, if any"
    sudo apt-get autoremove
    echoblue "---> Clear apt cache"
    sudo apt-get clean
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
fi

if [ $1 == "pycheckers" ] || [ $1 == "all" ];then
    echobold "===> SETTINGS UP CODE STYLE CHECKERS FOR EMACS AND GEANY"
    echoblue "---> Make ~/.emacs.d/lisp dir"
    mkdir -p ~/.emacs.d/lisp
    echoblue "---> Copy flymake-cursor.el to ~/.emacs.d/lisp dir"
    cp ~/PyExpLabSys/bootstrap/flymake-cursor.el ~/.emacs.d/lisp/
    echoblue "---> Copy .emacs to ~/.emacs.d/lisp dir"
    cp ~/PyExpLabSys/bootstrap/.emacs ~/
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

    echo ${PYTHONPATH}
    bashrc_addition="export PYTHONPATH=\${PYTHONPATH}:~/ABElectronics_Python_Libraries/ABElectronics_DeltaSigmaPi/"
    grep SigmaPi ~/.bashrc > /dev/null
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

    echogood "+++++> DONE"
fi


# Print message about resetting bash after bash modifications
if [ $reset_bash == "YES" ];then
    echo
    echobold "##> NOTE! ~/PyExpLabSys/bin has been added to PATH, which means"
    echobold "##> that the user specific rgit, kgit and agit commands (for "
    echobold "##> Robert, Kenneth and Anders) can be used."
    echobold "##>"
    echobold "##> NOTE! Your bash environment has been modified."
    echobold "##> Run: \"source ~/.bashrc\" to make the changes take effect."
fi
