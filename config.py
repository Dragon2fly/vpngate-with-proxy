# -*- coding: utf-8 -*-
__author__ = 'duc_tin'

import ConfigParser


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