#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"

# check py version
import sys
py_ver = sys.version_info[0:2]
if py_ver < (3, 6):
    print("This program required python3.6+ to run!")
    sys.exit(1)

from base import *
from subprocess import check_output, call

# initial basic parameters
user_home = sys.argv[1]
my_cfg = Setting()

# first time config
# check for existence of config files,
# and make a symlink to current directory
my_cfg.check()

# detect Debian based or Redhat based OS's package manager
pkg_mgr = None
check_ls = ["apt-get", "yum", "dnf"]
for pkg in check_ls:
    if check_output("whereis -b {}".format(pkg).split()).strip().split(b":")[1]:
        pkg_mgr = pkg

# check dependencies
required = {'openvpn': 0, 'python-requests': 0}

try:
    import requests
except ImportError:
    required['python-requests'] = 1

if not os.path.exists('/usr/sbin/openvpn'):
    required['openvpn'] = 1

need = [p for p in required if required[p]]
if need:
    print(ctext('\n**Lack of dependencies**', 'rB'))
    env = dict(os.environ)

    if my_cfg.network['use_proxy'] == 'yes':
        env['http_proxy'] = 'http://%s:%s' % (my_cfg.network['address'], my_cfg.network['port'])
        env['https_proxy'] = 'https://%s:%s' % (my_cfg.network['address'], my_cfg.network['port'])

    for package in need:
        print('\n___Now installing', ctext(package, 'gB'))
        print()
        call([pkg_mgr, '-y', 'install', package], env=env)