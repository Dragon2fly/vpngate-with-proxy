# -*- coding: utf-8 -*-
__author__ = 'duc_tin'

import ConfigParser
import re


def get_input(config_path, option):
    if option[0] in ['config']:
        proxy, port, sort_by, use_proxy = read_config(config_path)
        print '_Current settings:'
        print '___proxy: %s:%s' % (proxy, port)
        print '___sort servers by: ', sort_by
        print 'Connect to VPN through proxy: ', use_proxy

        while 1:
            print '\nPress Enter to process to vpn list or \n1: to change proxy\'s address\n2: to change proxy\'s ' \
                  'port\n3: to change sorting parameter\n4: to turn on/off proxy'
            user_input = raw_input()
            if user_input == '':
                print 'Process to vpn server list'
                write_config(config_path, proxy, port, sort_by, use_proxy)
                return
            elif user_input == '1':
                proxy = raw_input('Http proxy\'s address (eg: www.proxy.com or 123.11.22.33): ')
            elif user_input == '2':
                user_input = 'abc'
                while not re.findall(r'^\d+$', user_input.strip()):
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
            else:
                print 'Invalid input'


def read_config(config_path):
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_path)
    use_proxy = parser.get('proxy', 'use proxy')
    proxy = parser.get('proxy', 'address')
    port = parser.get('proxy', 'port')
    sort_by = parser.get('sort', 'key')
    return proxy, port, sort_by, use_proxy


def write_config(config_path, proxy, port, parameter, use_proxy):
    parser = ConfigParser.SafeConfigParser()
    parser.add_section('proxy')
    parser.set('proxy', 'use proxy', use_proxy)
    parser.set('proxy', 'address', proxy)
    parser.set('proxy', 'port', port)

    parser.add_section('sort')
    parser.set('sort', 'key', parameter)

    with open(config_path, 'w+') as configfile:
        parser.write(configfile)