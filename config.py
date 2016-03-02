#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"
__copyright__ = "Copyright 2015+, duc_tin"
__license__ = "GPLv2"
__version__ = "1.25"
__maintainer__ = "duc_tin"
__email__ = "nguyenbaduc.tin@gmail.com"

import ConfigParser
import re
import sys
import socket
from collections import OrderedDict


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


def get_input(s, option):
    """
    :type s: Setting
    """

    if option[0] not in ['c', 'config']:
        print 'Wrong argument. Do you mean "config" or "restore" ?'
        return

    while 1:
        use_proxy, proxy, port, ip, sort_by, s_country, s_port, fix_dns, dns, verbose, mirrors = s[:]
        mirrors = mirrors.split(', ')

        print ctext('\n Current settings:', 'B')
        print ctext('    1. Proxy address:', 'yB'), proxy, ctext('\t2. port: ', 'yB'), port
        print ctext('    3. Use proxy:', 'yB'), use_proxy
        print ctext('    4. Sort servers by:', 'yB'), sort_by
        print ctext('    5. Country filter:', 'yB'), s_country, ctext('\t\t6. VPN server\'s port: ', 'yB'), s_port
        print ctext('    7. Fix dns leaking:', 'yB'), fix_dns
        print ctext('    8. DNS list: ', 'yB'), dns
        print ctext('    9. Show openvpn log:', 'B'), verbose
        print ctext('   10. VPN gate\'s mirrors:', 'yB'), '%s ...' % mirrors[1]

        user_input = raw_input('\nCommand or just Enter to continue: ')
        if user_input == '':
            print 'Process to vpn server list'
            s.write()
            return
        elif user_input == '1':
            s.proxy['address'] = raw_input('Your http_proxy:')
            s.proxy['ip'] = socket.gethostbyname(proxy)
        elif user_input == '2':
            user_input = 'abc'
            while not user_input.strip().isdigit() and 0 <= int(user_input.strip()) <= 65535:
                user_input = raw_input('Http proxy\'s port (eg: 8080): ')
            s.proxy['port'] = user_input

        elif user_input == '3':
            while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                user_input = raw_input('Use proxy to connect to vpn? (yes|no): ')
            else:
                s.proxy['use_proxy'] = 'no' if user_input in 'no' else 'yes'

        elif user_input == '4':
            while user_input not in ['speed', 'ping', 'score', 'up time', 'uptime']:
                user_input = raw_input('Sort servers by (speed | ping | score | up time): ')
            s.sort['key'] = 'up time' if user_input == 'uptime' else user_input

        elif user_input == '5':
            while not re.match('^[a-z ]*$', user_input.lower().strip()):
                user_input = raw_input('Country\'s name (eg: all(default), jp, japan):')
            else:
                s.filter['country'] = 'all' if not user_input else user_input.lower()

        elif user_input == '6':
            user_input = 'abc'
            while not user_input.strip().isdigit():
                user_input = raw_input('VPN server\'s port (eg: 995): ')
                if not user_input or 'all' == user_input: break
            s.filter['port'] = user_input if user_input else 'all'

        elif user_input == '7':
            while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                user_input = raw_input('Fix DNS:')
            else:
                s.dns['fix_dns'] = 'no' if user_input in 'no' else 'yes'

        elif user_input == '8':
            print 'Default DNS are 8.8.8.8, 84.200.69.80, 208.67.222.222'
            user_input = '@'
            while not re.match('[a-zA-Z0-9., ]*$', user_input.strip()):
                user_input = raw_input('DNS server(s) with "," separated or Enter to use default:')
            if user_input:
                s.dns['dns'] = user_input.replace(' ', '').split(',')
            else:
                s.dns['dns'] = '8.8.8.8, 84.200.69.80, 208.67.222.222'

        elif user_input == '9':
            while user_input.lower() not in ['y', 'n', 'yes', 'no']:
                user_input = raw_input('Show openvpn log: ')
            else:
                s.openvpn['verbose'] = 'no' if user_input in 'no' else 'yes'

        elif user_input == '10':
            while True:
                user_input = "abc"
                print ctext('\n Current VPNGate\'s mirrors:', 'B')
                for ind, url in enumerate(mirrors):
                    print ' ', ind, url

                print '\nType ' + ctext("add %s", 'B') + ' or ' + ctext("del %d", 'B') + ' to add or delete mirror \n' \
                                                                                         '  where %s is a mirror\'s url and %d is index number of a mirror' \
                                                                                         '\n  Or just Enter to leave it intact'

                while user_input.lower()[0:3] not in ("add", "del", ""):
                    user_input = raw_input("\033[1mYour command: \033[0m")
                else:
                    if user_input.lower()[0:3] == "add":
                        url = user_input.lower()[3:].strip()
                        mirrors.append(url)
                    elif user_input.lower()[0:3] == "del":
                        number = user_input.lower()[3:].strip()
                        if number.isdigit() and int(number) < len(mirrors):
                            num = int(number)
                            mirrors.pop(num)
                        else:
                            print '  Index number is not exist!'
                    else:
                        s.mirror['url'] = ', '.join(mirrors)
                        break

        elif user_input in ['q', 'quit', 'exit']:
            print ctext('Goodbye'.center(40), 'gB')
            sys.exit(0)
        else:
            print 'Invalid input'


class Setting:
    def __init__(self, path):
        self.path = path
        self.parser = ConfigParser.SafeConfigParser()

        self.proxy = OrderedDict([('use_proxy', 'no'), ('address', ''),
                                  ('port', ''),
                                  ('ip', '')])

        self.sort = {'key': 'score'}

        self.filter = OrderedDict([('country', 'all'), ('port', 'all')])

        self.dns = OrderedDict([('fix_dns', 'yes'),
                                ('dns', '8.8.8.8, 8.8.8.8, 84.200.69.80, 208.67.222.222')])

        self.openvpn = {'verbose': 'yes'}

        self.mirror = {'url': "http://125.131.205.167:52806, "
                              "http://115.160.46.181:38061, "
                              "http://i121-114-60-223.s41.a028.ap.plala.or.jp:38715, "
                              "http://captkaos351.net:16691"}

        self.sections = OrderedDict([('proxy', self.proxy),
                                     ('sort', self.sort),
                                     ('country_filter', self.filter),
                                     ('DNS_leak', self.dns),
                                     ('openvpn', self.openvpn),
                                     ('mirror', self.mirror)])

    def __getitem__(self, index):
        data = []
        for sec in self.sections.values():
            data += sec.values()

        return data[index]

    def write(self):
        for sect in self.sections:
            if not self.parser.has_section(sect):
                self.parser.add_section(sect)
            for content in self.sections[sect]:
                self.parser.set(sect, content, self.sections[sect][content])

        with open(self.path, 'w+') as configfile:
            self.parser.write(configfile)

    def load(self):
        self.parser.read(self.path)

        for sect in self.sections:
            for content in self.sections[sect]:
                try:
                    self.sections[sect][content] = self.parser.get(sect, content)
                except ConfigParser.NoSectionError:
                    self.parser.add_section(sect)
                    self.parser.set(sect, content, self.sections[sect][content])
