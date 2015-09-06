#!/bin/bash
case "$script_type" in
  up)
        echo call script up
        mv /etc/resolv.conf /etc/resolv.conf.orig
        echo "nameserver 8.8.8.8" > /etc/resolv.conf
        ;;
  down)
        echo call script down
        cp -a /etc/resolv.conf.orig /etc/resolv.conf
        ;;
esac

