# -*- coding: utf-8 -*-
__author__ = 'duc_tin'

import ConfigParser
import os
import sys


def get_input(config_path, option):
    if option[0] in ['config']:
        proxy, port, sort_by = read_config(config_path)
        print '__Current settings:'
        print '___proxy: %s:%s' % (proxy, port)
        print '___sort servers by: ', sort_by

        while 1:
            print '\nPress Enter to process to vpn list or \n1: to change proxy\'s address\n2: to change port\n3: to ' \
                  'change sorting parameter'
            user_input = raw_input()
            if user_input == '':
                print 'Process to vpn server list'
                write_config(config_path, proxy, port, sort_by)
                return
            elif user_input == '1':
                proxy = raw_input('Http proxy\'s address (eg: www.proxy.com or 123.11.22.33): ')
            elif user_input == '2':
                port = raw_input('Http proxy\'s port (eg: 8080): ')
            elif user_input == '3':
                sort_by = raw_input('sort result by (speed | ping | up time): ')


def read_config(config_path):
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_path)
    proxy = parser.get('proxy', 'address')
    port = parser.get('proxy', 'port')
    sort_by = parser.get('sort', 'key')
    return proxy, port, sort_by


def write_config(config_path, proxy, port, parameter):
    parser = ConfigParser.SafeConfigParser()
    parser.add_section('proxy')
    parser.set('proxy', 'address', proxy)
    parser.set('proxy', 'port', port)

    parser.add_section('sort')
    parser.set('sort', 'key', parameter)

    with open(config_path, 'w+') as configfile:
        parser.write(configfile)