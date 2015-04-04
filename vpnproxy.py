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
        self.score = data[2]
        self.ping = int(data[3]) if data[3] != '-' else 'inf'
        self.speed = int(data[4])
        self.country = data[6]
        self.NumSessions = data[7]
        self.uptime = data[8]
        self.logPolicy = data[11]
        self.config_data = data[-1]

    def write_file(self):
        txt_data = base64.b64decode(self.config_data)
        add_proxy = txt_data.replace('\r\n;http-proxy-retry\r\n', '\r\nhttp-proxy-retry 5\r\n')
        added_proxy = add_proxy.replace('\r\n;http-proxy [proxy server] [proxy port]\r\n',
                                        '\r\nhttp-proxy %s %s\r\n' % (proxy, port))
        dns_fixed = added_proxy + Server.dns_leak_stop
        tmp_vpn = open('vpn_tmp', 'w+')
        tmp_vpn.write(dns_fixed)
        return tmp_vpn

    def __str__(self):
        speed = self.speed/1000.**2
        uptime = datetime.timedelta(milliseconds=int(self.uptime))
        uptime = re.split(',|\.', str(uptime))[0]
        return '\t  %s\t  %s ms    %.2f Mbps\t  %s\t %s'\
               % (self.country, self.ping, speed, uptime.ljust(7), self.logPolicy)


def get_data():
    try:
        vpn_data = requests.get('http://www.vpngate.net/api/iphone/', proxies=proxies, timeout=3).text.replace('\r', '')
        servers = [line.split(',') for line in vpn_data.split('\n')]
        servers = {s[0]: Server(s) for s in servers[2:] if len(s) > 1}
        return servers
    except requests.exceptions.ConnectionError:
        print 'Failed to get VPN servers data\nCheck your network setting and proxy'
    except requests.exceptions.ConnectTimeout:
        print 'Connection Timeout!\nCheck your network setting and proxy'

# proxy server and port
path = os.path.realpath(sys.argv[0])
config_file = os.path.split(path)[0] + '/config.ini'

if os.path.exists(config_file):
    proxy, port, sort_by = read_config(config_file)
else:
    proxy, port = raw_input(' Enter your http proxy:port\n(eg: www.proxy.com:8080 or 123.11.22.33:8080): ').split(':')
    sort_by = raw_input('sort result by (speed (default) | ping | score):')
    if sort_by not in ['speed', 'ping', 'score']:
        sort_by = 'speed'

    write_config(config_file, proxy, port, sort_by)

# process commandline arguments
args = sys.argv[1:]
if len(args):
    get_input(config_file, args)

proxies = {
    'http': 'http://' + proxy + ':' + port,
    'https': 'http://' + proxy + ':' + port,
}

# fetch data from vpngate.net
vpn_list = get_data()
ranked = sorted(vpn_list.keys(), key=lambda x: vpn_list[x].speed, reverse=True)

while True:
    print 'Index\t Country   Ping\t    Speed\t Up Time\t  Log Policy'
    for index, key in enumerate(ranked[:20]):
        print index, ':', vpn_list[key]
    try:
        user_input = raw_input('Choose vpn No.: ')
        if user_input in ['Q', 'q', 'quit', 'exit']:
            sys.exit()
        chose = int(user_input)
        print 'Connect to %s'.center(40) % vpn_list[ranked[chose]].ip
        vpn_file = vpn_list[ranked[chose]].write_file()
        vpn_file.close()
        call(['sudo', 'openvpn', '--config', os.path.abspath(vpn_file.name)])
    except KeyboardInterrupt:
        time.sleep(0.5)
        print "Select another VPN server or 'q' to quit"