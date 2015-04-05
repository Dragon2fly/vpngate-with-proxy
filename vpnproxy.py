#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'duc_tin'

import os
import sys
import re
import requests
import base64
import time
import datetime
from config import *
from subprocess import call


class Server():
    dns_leak_stop = 'script-security 2\r\nup update-resolv-conf.sh\r\ndown update-resolv-conf.sh\r\n'

    def __init__(self, data):
        self.ip = data[1]
        self.score = int(data[2])
        self.ping = int(data[3]) if data[3] != '-' else 'inf'
        self.speed = int(data[4])
        self.country_long = data[5]
        self.country_short = data[6]
        self.NumSessions = data[7]
        self.uptime = data[8]
        self.logPolicy = data[11]
        self.config_data = base64.b64decode(data[-1])
        self.proto = 'tcp' if '\r\nproto tcp\r\n' in self.config_data else 'udp'

    def write_file(self):
        txt_data = self.config_data
        if use_proxy == 'yes':
            txt_data = txt_data.replace('\r\n;http-proxy-retry\r\n', '\r\nhttp-proxy-retry 3\r\n')
            txt_data = txt_data.replace('\r\n;http-proxy [proxy server] [proxy port]\r\n',
                                        '\r\nhttp-proxy %s %s\r\n' % (proxy, port))
        dns_fixed = txt_data + Server.dns_leak_stop
        tmp_vpn = open('vpn_tmp', 'w+')
        tmp_vpn.write(dns_fixed)
        return tmp_vpn

    def __str__(self):
        speed = self.speed/1000.**2
        uptime = datetime.timedelta(milliseconds=int(self.uptime))
        uptime = re.split(',|\.', str(uptime))[0]
        txt = [self.country_short, str(self.ping), '%.2f' % speed, uptime, self.logPolicy, str(self.score), self.proto]
        txt = [dta.center(spaces[ind + 1]) for ind, dta in enumerate(txt)]
        return ''.join(txt)


def get_data():
    if use_proxy == 'yes':
        proxies = {
            'http': 'http://' + proxy + ':' + port,
            'https': 'http://' + proxy + ':' + port,
        }
    else:
        proxies = {}

    try:
        print 'Use proxy: ', use_proxy
        vpn_data = requests.get('http://www.vpngate.net/api/iphone/', proxies=proxies, timeout=3).text.replace('\r', '')
        servers = [line.split(',') for line in vpn_data.split('\n')]
        servers = {s[0]: Server(s) for s in servers[2:] if len(s) > 1}
        return servers
    except requests.exceptions.RequestException as e:
        print e
        print 'Failed to get VPN servers data\nCheck your network setting and proxy'
        sys.exit(1)


def refresh_data():
    # fetch data from vpngate.net
    vpnlist = get_data()

    if sort_by == 'speed':
        sort = sorted(vpnlist.keys(), key=lambda x: vpnlist[x].speed, reverse=True)
    elif sort_by == 'ping':
        sort = sorted(vpnlist.keys(), key=lambda x: vpnlist[x].ping)
    elif sort_by == 'score':
        sort = sorted(vpnlist.keys(), key=lambda x: vpnlist[x].score, reverse=True)
    elif sort_by == 'up time':
        sort = sorted(vpnlist.keys(), key=lambda x: vpnlist[x].uptime)
    else:
        print '\nValueError: sort_by must be in "speed|ping|score|up time" but got "%s" instead.' % sort_by
        print 'Change your setting by "$ ./vpnproxy config"\n'
        sys.exit()

    return sort, vpnlist

# ---------------------------- Main  --------------------------------

# get config file path
path = os.path.realpath(sys.argv[0])
config_file = os.path.split(path)[0] + '/config.ini'
args = sys.argv[1:]

# get proxy from config file
if os.path.exists(config_file):
    if len(args):
        # process commandline arguments
        get_input(config_file, args)

    proxy, port, sort_by, use_proxy = read_config(config_file)

else:
    use_proxy = raw_input('Use proxy to connect to vpn? (yes|no): ')
    proxy, port = raw_input(' Enter your http proxy:port\n(eg: www.proxy.com:8080 or 123.11.22.33:8080): ').split(':')
    sort_by = raw_input('sort result by (speed (default) | ping | score | up time):')
    if sort_by not in ['speed', 'ping', 'score', 'up time']:
        sort_by = 'speed'

    write_config(config_file, proxy, port, sort_by, use_proxy)

ranked, vpn_list = refresh_data()

labels = ['Index', 'Country', 'Ping', 'Speed', 'Up time', 'Log Policy', 'Score', 'protocol']
spaces = [6, 7, 6, 10, 10, 10, 10, 10]
labels = [label.center(spaces[ind]) for ind, label in enumerate(labels)]

while True:
    print ''.join(labels)
    for index, key in enumerate(ranked[:20]):
        print '%2d:'.center(6) % index, vpn_list[key]
    try:
        user_input = raw_input('Choose vpn No.: ')
        if user_input.strip().lower() in ['q', 'quit', 'exit']:
            sys.exit()
        elif user_input.strip().lower() in ['r', 'refresh']:
            ranked, vpn_list = refresh_data()
        elif user_input.strip().lower() == 'config':
            get_input(config_file, [user_input])
            proxy, port, sort_by, use_proxy = read_config(config_file)
            ranked, vpn_list = refresh_data()
        elif re.findall(r'^\d+$', user_input.strip()) and int(user_input) < 20:
            chose = int(user_input)
            print ('Connect to ' + vpn_list[ranked[chose]].country_long).center(40)
            print vpn_list[ranked[chose]].ip.center(40)
            vpn_file = vpn_list[ranked[chose]].write_file()
            vpn_file.close()
            call(['sudo', 'openvpn', '--config', os.path.abspath(vpn_file.name)])
        else:
            print 'Invalid command!'
            print ' q(uit) to quit\n r(efresh) to refresh table\n' \
                  ' config to change setting\n number in range 0~19 to choose vpn'
            time.sleep(3)
    except KeyboardInterrupt:
        time.sleep(0.5)
        print "\nSelect another VPN server or 'q' to quit"