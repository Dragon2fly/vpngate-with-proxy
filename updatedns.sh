#!/bin/bash
case "$script_type" in
  up)
        mv /etc/resolv.conf /etc/resolv.conf.orig
        echo "nameserver 8.8.8.8" > /etc/resolv.conf
        ;;
  down)
        cp -a /etc/resolv.conf.orig /etc/resolv.conf
        ;;
esac

