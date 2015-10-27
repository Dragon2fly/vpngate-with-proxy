#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"
__copyright__ = "Copyright 2015+, duc_tin"
__license__ = "GPLv2"
__version__ = "1.0"
__maintainer__ = "duc_tin"
__email__ = "nguyenbaduc.tin@gmail.com"

import ConfigParser
import re
import sys
import socket


def ctext(text, color):
    """ Add color to printed text
    :type text: str
    :type color: str
    """
    fcolor = {'p': '\033[95m',  # purple
              'b': '\033[94m',  # blue
              'g': '\033[92m',  # green
              'y': '\033[93m',  # yellow
              'r': '\033[91m',  # red

              'B': '\033[1m',  # BOLD
              'U': '\033[4m',  # UNDERLINE
              }

    ENDC = '\033[0m'

    tformat = ''.join([fcolor[fm] for fm in color])

    return tformat + text + ENDC


def get_input(config_path, option):
    if option[0] in ['c', 'config']:
        proxy, port, ip, sort_by, use_proxy, country, fix_dns, dns, verbose = read_config(config_path)

        while 1:
            print ctext('\n Current settings:', 'B')
            print ctext('   1. Proxy address:', 'yB'), proxy, ctext('\t2. port: ', 'yB'), port
            print ctext('   3. Use proxy:', 'yB'), use_proxy
            print ctext('   4. Sort servers by:', 'yB'), sort_by
            print ctext('   5. Country filter:', 'yB'), country
            print ctext('   6. Fix dns leaking:', 'yB'), fix_dns
            print ctext('   7. DNS list: ', 'yB'), dns
            print ctext('   8. Show openvpn log:', 'B'), verbose

            user_input = raw_input('\nCommand or Enter to fetch server list: ')
            if user_input == '':
                print 'Process to vpn server list'
                write_config(config_path, proxy, port, ip, sort_by, use_proxy, country, fix_dns, dns, verbose)
                return
            elif user_input == '1':
                proxy = raw_input('Your http_proxy:')
                ip = socket.gethostbyname(proxy)
            elif user_input == '2':
                user_input = 'abc'
                while not user_input.strip().isdigit():
                    user_input = raw_input('Http proxy\'s port (eg: 8080): ')
                port = user_input

            elif user_input == '3':
                while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                    user_input = raw_input('Use proxy to connect to vpn? (yes|no): ')
                else:
                    use_proxy = 'no' if user_input in 'no' else 'yes'

            elif user_input == '4':
                while user_input not in ['speed', 'ping', 'score', 'up time', 'uptime']:
                    user_input = raw_input('Sort servers by (speed | ping | score | up time): ')
                sort_by = 'up time' if user_input == 'uptime' else user_input

            elif user_input == '5':
                while not re.match('^[a-z ]*$', user_input.lower().strip()):
                    user_input = raw_input('Country\'s name (eg: all(default), jp, japan):')
                else:
                    country = 'all' if not user_input else user_input.lower()

            elif user_input == '6':
                while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                    user_input = raw_input('Fix DNS:')
                else:
                    fix_dns = 'no' if user_input in 'no' else 'yes'

            elif user_input == '7':
                print 'Default DNS are 8.8.8.8, 84.200.69.80, 208.67.222.222'
                user_input='@'
                while not re.match('[a-zA-Z0-9., ]*$', user_input.strip()):
                    user_input = raw_input('DNS server(s) with "," separated or Enter to use default:')
                if user_input:
                    dns = user_input.replace(' ', '').split(',')
                else:
                    dns = '8.8.8.8, 84.200.69.80, 208.67.222.222'

            elif user_input == '8':
                while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                    user_input = raw_input('Use proxy to connect to vpn? (yes|no): ')
                else:
                    verbose = 'no' if user_input in 'no' else 'yes'

            elif user_input in ['q', 'quit', 'exit']:
                print ctext('Goodbye'.center(40), 'gB')
                sys.exit(0)
            else:
                print 'Invalid input'

    else:
        print 'Wrong argument. Do you mean "config" or "restore" ?'


def read_config(config_path):
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_path)
    use_proxy = parser.get('proxy', 'use proxy')
    proxy = parser.get('proxy', 'address')
    port = parser.get('proxy', 'port')
    ip = parser.get('proxy', 'ip')
    sort_by = parser.get('sort', 'key')
    country = parser.get('country_filter', 'country')
    fix_dns = parser.get('DNS_leak', 'fix_dns')
    dns = parser.get('DNS_leak', 'dns')
    verbose = parser.get('openvpn', 'verbose')
    return proxy, port, ip, sort_by, use_proxy, country, fix_dns, dns, verbose


def write_config(config_path, proxy, port, ip, parameter, use_proxy, country, fix_dns, dns, verbose='no'):
    parser = ConfigParser.SafeConfigParser()
    parser.add_section('proxy')
    parser.set('proxy', 'use proxy', use_proxy)
    parser.set('proxy', 'address', proxy)
    parser.set('proxy', 'port', port)
    parser.set('proxy', 'ip', ip)

    parser.add_section('sort')
    parser.set('sort', 'key', parameter)

    parser.add_section('country_filter')
    parser.set('country_filter', 'country', country)

    parser.add_section('DNS_leak')
    parser.set('DNS_leak', 'fix_dns', fix_dns)
    parser.set('DNS_leak', 'dns', dns)

    parser.add_section('openvpn')
    parser.set('openvpn', 'verbose', verbose)

    with open(config_path, 'w+') as configfile:
        parser.write(configfile)