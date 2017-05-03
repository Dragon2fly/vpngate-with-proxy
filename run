#!/bin/bash

# allow running from anywhere
# when making an alias in .bashrc or /etc/environment: vpn="path/to/./run"

dir=$(cd -P -- "$(dirname -- "$0")" && pwd -P)
cd "$(dirname "$(realpath "$0")")";
echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"

user_home=($HOME)
type=$1
arg=$2

if [ "$type" == "cli" ]; then
    sudo python vpnproxy_cli.py $user_home $arg
else
    if [ "$type" != "tui" ]; then
        arg=$type
    fi

    # check if this os is *buntu and launch vpn_indicator
    os_id=`cat /proc/version`
    target="buntu"
    test "${os_id#*$target}" != "$os_id" && stdbuf -oL python vpn_indicator.py > logs/indicator.log &

    sleep 0.2
    sudo python vpnproxy_tui.py $user_home $arg
fi
