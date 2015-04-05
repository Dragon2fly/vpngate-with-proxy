# -*- coding: utf-8 -*-
__author__ = 'duc_tin'

import ConfigParser
import re


def get_input(config_path, option):
    if option[0] in ['config']:
        proxy, port, sort_by, use_proxy, country = read_config(config_path)
        print ' Current settings:'
        print '   1. Proxy address: %s\t2. port: %s' % (proxy, port)
        print '   3. Sort servers by: ', sort_by
        print '   4. Connect to VPN through proxy: ', use_proxy
        print '   5. Country filter: ', country

        while 1:
            user_input = raw_input('\nCommand or Enter to fetch server list: ')
            if user_input == '':
                print 'Process to vpn server list'
                write_config(config_path, proxy, port, sort_by, use_proxy, country)
                return
            elif user_input == '1':
                proxy = raw_input('Http proxy\'s address (eg: www.proxy.com or 123.11.22.33): ')
            elif user_input == '2':
                user_input = 'abc'
                while not user_input.strip().isdigit():
                    user_input = raw_input('Http proxy\'s port (eg: 8080): ')
                port = user_input
            elif user_input == '3':
                while user_input not in ['speed', 'ping', 'score', 'up time', 'uptime']:
                    user_input = raw_input('sort result by (speed | ping | score | up time): ')
                sort_by = 'up time' if user_input == 'uptime' else user_input

            elif user_input == '4':
                while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                    user_input = raw_input('Use proxy to connect to vpn? (yes|no): ')
                else:
                    use_proxy = 'no' if user_input in 'no' else 'yes'

            elif user_input == '5':
                while not re.match('^[a-z ]+$', user_input.lower().strip()):
                    user_input = raw_input('Country\'s name (eg: all(default), jp, japan):')
                else:
                    country = user_input
            else:
                print 'Invalid input'


def read_config(config_path):
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_path)
    use_proxy = parser.get('proxy', 'use proxy')
    proxy = parser.get('proxy', 'address')
    port = parser.get('proxy', 'port')
    sort_by = parser.get('sort', 'key')
    country = parser.get('country_filter', 'country')
    return proxy, port, sort_by, use_proxy, country


def write_config(config_path, proxy, port, parameter, use_proxy, country):
    parser = ConfigParser.SafeConfigParser()
    parser.add_section('proxy')
    parser.set('proxy', 'use proxy', use_proxy)
    parser.set('proxy', 'address', proxy)
    parser.set('proxy', 'port', port)

    parser.add_section('sort')
    parser.set('sort', 'key', parameter)

    parser.add_section('country_filter')
    parser.set('country_filter', 'country', country)

    with open(config_path, 'w+') as configfile:
        parser.write(configfile)