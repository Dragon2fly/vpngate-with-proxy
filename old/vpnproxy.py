#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'duc_tin'

import os
import sys
import base64
import time
import datetime
import random
from config import *
from subprocess import call, Popen, PIPE

mirrors = ['http://www.vpngate.net',
           'http://103.253.112.16:49882',
           'http://158.ip-37-187-34.eu:58272',
           'http://121.186.216.97:38438',
           'http://hannan.postech.ac.kr:6395',
           'http://115.160.46.181:38061',
           'http://hornet.knu.ac.kr:36171',
           'http://182-166-242-138f1.osk3.eonet.ne.jp:64298',]


class Server():
    if os.path.exists('/sbin/resolvconf'):
        # dns_leak_stop = 'script-security 2\r\nup update-resolv-conf.sh\r\ndown update-resolv-conf.sh\r\n'
        dns_leak_stop = 'script-security 2\r\nup updatedns.sh\r\ndown updatedns.sh\r\n'

    else:
        print ''
        dns_leak_stop = ''

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

        if dns_fix == 'yes':
            txt_data += Server.dns_leak_stop

        tmp_vpn = open('vpn_tmp', 'w+')
        tmp_vpn.write(txt_data)
        return tmp_vpn

    def __str__(self):
        speed = self.speed / 1000. ** 2
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

    i = 0
    while i < len(mirrors):
        try:
            print ctext('using gate: ', 'B'),  mirrors[i]
            gate = mirrors[i] + '/api/iphone/'
            vpn_data = requests.get(gate, proxies=proxies, timeout=3).text.replace('\r', '')

            if 'vpn_servers' not in vpn_data:
                raise requests.exceptions.RequestException

            servers = [line.split(',') for line in vpn_data.split('\n')]
            servers = {s[0]: Server(s) for s in servers[2:] if len(s) > 1}
            return servers
        except requests.exceptions.RequestException as e:
            print e
            print 'Connection to gate ' + ctext(mirrors[i], 'B') + ctext(' failed\n', 'rB')
            i += 1
    else:
        print 'Failed to get VPN servers data\nCheck your network setting and proxy'
        sys.exit(1)


def refresh_data():
    # fetch data from vpngate.net
    vpnlist = get_data()
    if country != 'all':
        vpnlist = dict([vpn for vpn in vpnlist.items()
                        if re.search(r'\b%s\b' % country, vpn[1].country_long.lower() + ' '
                                     + vpn[1].country_short.lower())])

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

    proxy, port, sort_by, use_proxy, country, dns_fix = read_config(config_file)

else:
    use_proxy = 'no' if raw_input('Do you need proxy to connect .? (yes|no): ') in 'no' else 'yes'
    if use_proxy == 'yes':
        print ' Input your http proxy such as' + ctext('www.abc.com:8080','pB')
        proxy, port = raw_input(' Your\033[95m proxy:port \033[0m:').split(':')
    else:
        proxy, port = '', ''
    sort_by = raw_input('Sort servers by [speed (default) | ping | score | up time]:')
    if sort_by not in ['speed', 'ping', 'score', 'up time']:
        sort_by = 'speed'
    country = raw_input('Filter server by country [eg: all(default), jp, japan]:')
    if not country:
        country = 'all'

    dns_fix = 'yes' if raw_input(' Fix DNS leaking [yes (default) | no] : ') in 'yes' else 'no'

    write_config(config_file, proxy, port, sort_by, use_proxy, country, dns_fix)

# ------------------- check_dependencies: ----------------------
required = {'openvpn': 0, 'python-requests': 0, 'resolvconf': 0}

try:
    import requests
except ImportError:
    required['python-requests'] = 1

# openvpn = Popen(['whereis', 'openvpn'], stdout=PIPE).stdout.read()
if not os.path.exists('/usr/sbin/openvpn'):
    required['openvpn'] = 1

if not os.path.exists('/sbin/resolvconf'):
    required['resolvconf'] = 1

need = [p for p in required if required[p]]
if need:
    print ctext('\n**Lack of dependencies**','rB')
    env = dict(os.environ)
    env['http_proxy'] = 'http://' + proxy + ':' + port
    env['https_proxy'] = 'http://' + proxy + ':' + port

    for package in need:
        print '\n___Now installing', ctext(package, 'gB')
        print
        call(['sudo', '-E', 'apt-get', 'install', package], env=env)

    import requests

# -------- all dependencies should be available after this line ----------------------
ranked, vpn_list = refresh_data()

labels = ['Index', 'Country', 'Ping', 'Speed', 'Up time', 'Log Policy', 'Score', 'protocol']
spaces = [6, 7, 6, 10, 10, 10, 10, 8]
labels = [label.center(spaces[ind]) for ind, label in enumerate(labels)]
connected_servers = []

while True:
    print ctext('Use proxy: ', 'B'), use_proxy,
    print ' || ', ctext('Country: ', 'B'), country

    if not ranked:
        print '\nNo server found for "%s"\n' % country
    else:
        print ctext(''.join(labels), 'gB')
        for index, key in enumerate(ranked[:20]):
            text = '%2d:'.center(6) % index + str(vpn_list[key])
            if connected_servers and vpn_list[key].ip == connected_servers[-1]:
                text = ctext(text, 'y')
            elif connected_servers and vpn_list[key].ip in connected_servers:
                text = ctext(text, 'r')
            print text

    try:
        server_sum = min(len(ranked), 20)
        user_input = raw_input(ctext('Vpn command: ', 'gB'))
        if user_input.strip().lower() in ['q', 'quit', 'exit']:
            sys.exit()
        elif user_input.strip().lower() in 'refresh':
            ranked, vpn_list = refresh_data()
        elif user_input.strip().lower() in 'config':
            get_input(config_file, [user_input])
            proxy, port, sort_by, use_proxy, country, dns_fix = read_config(config_file)
            ranked, vpn_list = refresh_data()
        elif re.findall(r'^\d+$', user_input.strip()) and int(user_input) < server_sum:
            chose = int(user_input)
            print ('Connect to ' + vpn_list[ranked[chose]].country_long).center(40)
            print vpn_list[ranked[chose]].ip.center(40)
            connected_servers.append(vpn_list[ranked[chose]].ip)
            vpn_file = vpn_list[ranked[chose]].write_file()
            vpn_file.close()
            call(['sudo', 'openvpn', '--config', os.path.abspath(vpn_file.name)])
        else:
            print 'Invalid command!'
            print '  q(uit) to quit\n  r(efresh) to refresh table\n' \
                  '  c(onfig) to change setting\n  number in range 0~%s to choose vpn\n' % (server_sum - 1)
            time.sleep(2)

    except KeyboardInterrupt:
        time.sleep(0.5)
        print "\nSelect another VPN server or 'q' to quit"
