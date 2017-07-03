#!/bin/bash


# This script sets up locale and keyboard

# Setup keyboard
#
# This changes the line that starts with XKBLAYOUT in
# /etc/default/keyboard to: XKBLAYOUT="dk"
echo "Making changes in /etc/default/keyboard"
echo "Current keyboard layout line:" `grep XKBLAYOUT /etc/default/keyboard`
sudo sed -i -e 's/XKBLAYOUT.*/XKBLAYOUT="dk"/g' /etc/default/keyboard
echo "Keyboard line after change:" `grep XKBLAYOUT /etc/default/keyboard`

# Change time zone
echo
echo "Making changes in /etc/timezone"
echo "Current time zone setting:" `cat /etc/timezone`
sudo sudo sed -i -e 's/.*/Europe\/Copenhagen/g' /etc/timezone
echo "Time zone after change:" `cat /etc/timezone`

# Reboot
read -p "Press [Enter] to reboot..."
sudo reboot
