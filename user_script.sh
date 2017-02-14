#!/bin/bash
# This file must be bash script.
# If you need sh/csh/ksh ... then call them within this file.
# This file will be executed with "root" privilege!
# Drop privilege by: su user_name -c "cmd to run"
# DNS should be changed within main program, not here!
# If you manually change your DNS here, you should turn of 'DNS fix' of main program.

# setup any environment variable that you need
set -e
export PATH="$PATH:/usr/sbin:/sbin"

USER=$(whoami)
echo $USER

# Don't modified this block
case "$1" in
up)
    # _____ your code here _____
    echo "called Up script"
    notify-send "$(hostname): LINK IS UP." --icon=network-idle

    # _____ end up script ______
;;
down)
    # _____ your code here _____
    echo "called Down script"
    notify-send "$(hostname): LINK IS DOWN !" --icon=dialog-error

    # _____ end down script ____
;;
esac

# anything outside "case" block will be executed twice!
