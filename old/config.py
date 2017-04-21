# -*- coding: utf-8 -*-
__author__ = 'duc_tin'

import ConfigParser
import re
import sys


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
        proxy, port, sort_by, use_proxy, country, fix_dns = read_config(config_path)

        while 1:
            print ctext(' Current settings:', 'B')
            print ctext('   1. Proxy address:', 'yB'), proxy, ctext('\t2. port: ', 'yB'), port
            print ctext('   3. Sort servers by:', 'gB'), sort_by
            print ctext('   4. Use proxy:', 'rB'), use_proxy
            print ctext('   5. Country filter:', 'pB'), country
            print ctext('   6. Fix dns leaking:', 'bB'), fix_dns

            user_input = raw_input('\nCommand or Enter to fetch server list: ')
            if user_input == '':
                print 'Process to vpn server list'
                write_config(config_path, proxy, port, sort_by, use_proxy, country, fix_dns)
                return
            elif user_input == '1':
                proxy = raw_input('Your http_proxy:')
            elif user_input == '2':
                user_input = 'abc'
                while not user_input.strip().isdigit():
                    user_input = raw_input('Http proxy\'s port (eg: 8080): ')
                port = user_input
            elif user_input == '3':
                while user_input not in ['speed', 'ping', 'score', 'up time', 'uptime']:
                    user_input = raw_input('Sort servers by (speed | ping | score | up time): ')
                sort_by = 'up time' if user_input == 'uptime' else user_input

            elif user_input == '4':
                while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                    user_input = raw_input('Use proxy to connect to vpn? (yes|no): ')
                else:
                    use_proxy = 'no' if user_input in 'no' else 'yes'

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
            elif user_input in ['q', 'quit', 'exit']:
                print ctext('Goodbye'.center(40), 'gB')
                sys.exit(0)
            else:
                print 'Invalid input'

    else:
        print 'Wrong argument. Do you mean "config"?'


def read_config(config_path):
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_path)
    use_proxy = parser.get('proxy', 'use proxy')
    proxy = parser.get('proxy', 'address')
    port = parser.get('proxy', 'port')
    sort_by = parser.get('sort', 'key')
    country = parser.get('country_filter', 'country')
    fix_dns = parser.get('DNS_leak', 'fix_dns')
    return proxy, port, sort_by, use_proxy, country, fix_dns


def write_config(config_path, proxy, port, parameter, use_proxy, country, fix_dns):
    parser = ConfigParser.SafeConfigParser()
    parser.add_section('proxy')
    parser.set('proxy', 'use proxy', use_proxy)
    parser.set('proxy', 'address', proxy)
    parser.set('proxy', 'port', port)

    parser.add_section('sort')
    parser.set('sort', 'key', parameter)

    parser.add_section('country_filter')
    parser.set('country_filter', 'country', country)

    parser.add_section('DNS_leak')
    parser.set('DNS_leak', 'fix_dns', fix_dns)

    with open(config_path, 'w+') as configfile:
        parser.write(configfile)