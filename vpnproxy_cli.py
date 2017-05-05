#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"
__copyright__ = "Copyright 2015+, duc_tin"
__license__ = "GPLv2"
__version__ = "1.35"
__maintainer__ = "duc_tin"
__email__ = "nguyenbaduc.tin@gmail.com"

import os
import signal
import base64
import time
import datetime
from config import *
from Queue import Queue
from threading import Thread
from subprocess import call, Popen, PIPE, check_output

# Get sudo privilege
euid = os.geteuid()
if euid != 0:
    # args = ['sudo', '-E', sys.executable] + sys.argv + [os.environ]
    # os.execlpe('sudo', *args)
    raise RuntimeError('Permission deny! You need to "sudo" or use "./run cli" instead')

# detect Debian based or Redhat based OS's package manager
pkg_mgr = None
check_ls = ["apt-get", "yum", "dnf"]
for pkg in check_ls:
    if check_output("whereis -b {}".format(pkg).split()).strip().split(":")[1]:
        pkg_mgr = pkg

# Define some mirrors of vpngate.net
mirrors = ["http://www.vpngate.net"]  # add your mirrors to config.ini file, not here

# TODO: add user manual to this and can be access by h, help.
# add option to change DNS differ from google


class Server:
    def __init__(self, data):
        self.ip = data[1]
        self.score = int(data[2])
        self.ping = int(data[3]) if data[3] != '-' else 'inf'
        self.speed = int(data[4])
        self.country_long = data[5]
        self.country_short = data[6]
        self.NumSessions = data[7]
        self.uptime = data[8]
        self.logPolicy = "2wk" if data[11]=="2weeks" else "inf"
        self.config_data = base64.b64decode(data[-1])
        self.proto = 'tcp' if '\r\nproto tcp\r\n' in self.config_data else 'udp'
        port = re.findall('remote .+ \d+', self.config_data)
        if not port:
            self.port = '1'
        else:
            self.port = port[0].split()[-1]

    def write_file(self):
        txt_data = self.config_data
        if use_proxy == 'yes':
            txt_data = txt_data.replace('\r\n;http-proxy-retry\r\n', '\r\nhttp-proxy-retry 3\r\n')
            txt_data = txt_data.replace('\r\n;http-proxy [proxy server] [proxy port]\r\n',
                                        '\r\nhttp-proxy %s %s\r\n' % (proxy, port))

        extra_option = ['keepalive 5 30\r\n',  # prevent connection drop due to inactivity timeout
                        'connect-retry 2\r\n']
        if True:
            index = txt_data.find('client\r\n')
            txt_data = txt_data[:index] + ''.join(extra_option) + txt_data[index:]

        tmp_vpn = open('vpn_tmp', 'w+')
        tmp_vpn.write(txt_data)
        return tmp_vpn

    def __str__(self):
        speed = self.speed / 1000. ** 2
        uptime = datetime.timedelta(milliseconds=int(self.uptime))
        uptime = re.split(',|\.', str(uptime))[0]
        txt = [self.country_short, str(self.ping), '%.2f' % speed, uptime, self.logPolicy, str(self.score), self.proto,
               self.ip, self.port]
        txt = [dta.center(spaces[ind + 1]) for ind, dta in enumerate(txt)]
        return ''.join(txt)


def get_data():
    global proxy
    if use_proxy == 'yes':
        ping_name = ['ping', '-w 2', '-c 2', proxy]
        ping_ip = ['ping', '-w 2', '-c 2', ip]
        res1, err1 = Popen(ping_name, stdout=PIPE, stderr=PIPE).communicate()
        res2, err2 = Popen(ping_ip, stdout=PIPE, stderr=PIPE).communicate()

        if err1 and not err2:
            print ctext('Warning: ', 'yB'),
            print "Cannot resolve proxy's hostname"
            proxy = ip
        if err1 and err2:
            print ' Ping proxy got error: ', ctext(err1, 'r')
            print ' Check your proxy setting'
        if not err1 and '100% packet loss' in res1:
            print ctext('Warning:', 'yB') + ctext('Proxy not response to ping', 'y')
            print ctext("Either proxy's security not allow it to response to ping packet\n or proxy itself is dead",
                        'y')

        proxies = {
            'http': 'http://' + proxy + ':' + port,
            'https': 'http://' + proxy + ':' + port,
        }

    else:
        proxies = {}

    i = 0
    while i < len(mirrors):
        try:
            print ctext('using gate: ', 'B'), mirrors[i]
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
    print "fetching data"
    vpnlist = get_data()

    if s_country != 'all':
        vpnlist = dict([vpn for vpn in vpnlist.items()
                        if re.search(r'\b%s\b' % s_country, vpn[1].country_long.lower() + ' '
                                     + vpn[1].country_short.lower())])
    if s_port != 'all':
        if port[0] == '>':
            vpnlist = dict([vpn for vpn in vpnlist.items() if int(vpn[1].port) > int(s_port[1:])])
        elif port[0] == '<':
            vpnlist = dict([vpn for vpn in vpnlist.items() if int(vpn[1].port) < int(s_port[1:])])
        else:
            vpnlist = dict([vpn for vpn in vpnlist.items() if vpn[1].port in s_port])

    if s_score != 'all':
        vpnlist = dict([vpn for vpn in vpnlist.items() if int(vpn[1].score) > int(s_score)])

    print "Filtering out dead VPN..."
    probe(vpnlist)

    if sort_by == 'speed':
        sort = sorted(vpnlist.keys(), key=lambda x: vpnlist[x].speed, reverse=True)
    elif sort_by == 'ping':
        sort = sorted(vpnlist.keys(), key=lambda x: vpnlist[x].ping)
    elif sort_by == 'score':
        sort = sorted(vpnlist.keys(), key=lambda x: vpnlist[x].score, reverse=True)
    elif sort_by == 'up time':
        sort = sorted(vpnlist.keys(), key=lambda x: int(vpnlist[x].uptime))
    else:
        print '\nValueError: sort_by must be in "speed|ping|score|up time" but got "%s" instead.' % sort_by
        print 'Change your setting by "$ ./vpnproxy config"\n'
        sys.exit()

    return sort, vpnlist


def probe(vpndict):
    """ Filter out fetched dead Vpn Servers
    """

    def is_alive(servers, queue):
        global ip, port  # of proxy
        target = [(vpndict[name].ip, vpndict[name].port) for name in servers]

        if use_proxy == 'yes':
            for i in range(len(target)):
                s = socket.socket()
                s.settimeout(test_timeout)
                s.connect((ip, int(port)))  # connect to proxy server
                ip_, port_ = target[i]
                data = 'CONNECT %s:%s HTTP/1.0\r\n\r\n' % (ip_, port_)
                s.send(data)
                dead = False
                try:
                    response = s.recv(100)
                except socket.timeout:
                    dead = True

                s.shutdown(socket.SHUT_RD)
                s.close()

                if dead or "200 Connection established" not in response:
                    queue.put(servers[i])
                time.sleep(test_interval)  # avoid DDos your proxy

        else:
            for i in range(len(target)):
                s = socket.socket()
                s.settimeout(test_timeout)
                ip, port = target[i]
                try:
                    s.connect((ip, int(port)))
                    s.shutdown(socket.SHUT_RD)
                except socket.timeout:
                    queue.put(servers[i])
                except Exception as e:
                    #print e
                    queue.put(servers[i])
                finally:
                    s.close()
                    # time.sleep(self.test_interval)      # no need since we make connection to different servers

    my_queue = Queue()
    chunk_len = 10  # reduce chunk_len will increase number of thread
    my_chunk = [vpndict.keys()[i:i + chunk_len] for i in range(0, len(vpndict), chunk_len)]
    my_thread = []
    for chunk in my_chunk:
        t = Thread(target=is_alive, args=(chunk, my_queue))
        t.start()
        my_thread.append(t)

    for t in my_thread: t.join()

    count = 0
    total = len(vpndict)
    while not my_queue.empty():
        count += 1
        dead_server = my_queue.get()
        del vpndict[dead_server]

    print 'Deleted %d dead servers out of %d' % (count, total)


def post_action(when):
    """ Change DNS, and do additional behaviors defined by user in user_script.sh"""
    if when == 'up':
        dns_manager('change', dns)

        # call user_script
        up = 'bash user_script.sh up'.split()
        call(up)

    elif when == 'down':
        dns_manager('restore')

        # call user_script
        down = 'bash user_script.sh down'.split()
        call(down)


def dns_manager(action='backup', DNS='8.8.8.8'):
    global dns_fix

    dns_orig = '/etc/resolv.conf.bak'

    if not os.path.exists(dns_orig):
        print ctext('Backup DNS setting', 'yB')
        backup = ['-aL', '/etc/resolv.conf', '/etc/resolv.conf.bak']
        call(['cp'] + backup)

    if action == "change" and dns_fix == 'yes':
        DNS = DNS.replace(' ', '').split(',')

        with open('/etc/resolv.conf', 'w+') as resolv:
            for dns in DNS:
                resolv.write('nameserver ' + dns + '\n')
        print ctext('\nChanged DNS', 'yB').center(38)

    elif action == "restore":
        print ctext('\nRestore DNS', 'yB')
        reverseDNS = ['-a', '/etc/resolv.conf.bak', '/etc/resolv.conf']
        call(['cp'] + reverseDNS)


def vpn_manager(ovpn):
    """ Check VPN season
        If vpn tunnel break or fail to create, terminate vpn season
        So openvpn not keep sending requests to proxy server and
         save you from being blocked.
    """
    global dns, verbose, dropped_time

    command = ['openvpn', '--config', ovpn]
    p = Popen(command, stdout=PIPE, stdin=PIPE)
    try:
        while p.poll() is None:
            line = p.stdout.readline()
            if verbose == 'yes':
                print line,
            if 'Initialization Sequence Completed' in line:
                dropped_time = 0
                post_action('up')
                print ctext('VPN tunnel established successfully'.center(40), 'B')
                print 'Ctrl+C to quit VPN'.center(40)
            elif 'Restart pause, ' in line and dropped_time <= max_retry:
                dropped_time += 1
                print ctext('Vpn has restarted %s time' % dropped_time, 'rB')
            elif dropped_time == max_retry or 'Connection timed out' in line or 'Cannot resolve' in line:
                dropped_time = 0
                print line
                print ctext('Terminate vpn', 'B')
                p.send_signal(signal.SIGINT)
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()
        print ctext('VPN tunnel is terminated'.center(40), 'B')
    finally:
        post_action('down')


def signal_term_handler(signal, frame):
    global SIGTERM
    print '\nGot SIGTERM, start exiting\n'
    SIGTERM = 1
    raise KeyboardInterrupt

# ---------------------------- Main  --------------------------------
# dead gracefully
signal.signal(signal.SIGTERM, signal_term_handler)
SIGTERM = 0

# anti dropping
dropped_time = 0
max_retry = 3

# test if alive
test_interval = 0.25
test_timeout = 1

# get config file path
user_home = sys.argv[1]
path = os.path.realpath(sys.argv[0])
config_file = user_home + '/.config/vpngate-with-proxy/config.ini'
user_script_file = user_home + '/.config/vpngate-with-proxy/user_script.sh'
cfg = Setting(config_file)
args = sys.argv[2:]

# get proxy from config file
if os.path.exists(config_file):
    cfg.load()
    if len(args):
        # process commandline arguments
        if args[0] in ['r', 'restore']:
            dns_manager('restore')
        else:
            get_input(cfg, args)

else:
    if not os.path.exists(user_home+'/.config/vpngate-with-proxy'):
        os.makedirs(user_home+'/.config/vpngate-with-proxy')

    print '\n' + '_' * 12 + ctext(' First time config ', 'gB') + '_' * 12 + '\n'

    cfg.proxy['use_proxy'] = 'no' if raw_input(
        ctext('Do you need proxy to connect? ', 'B') + '(yes|[no]):') in 'no' else 'yes'
    if cfg.proxy['use_proxy'] == 'yes':
        proxy = port = ip = ''
        useit = 'no'

        if "http_proxy" in os.environ:
            proxy, port = os.environ['http_proxy'].strip('/').split('//')[1].split(':')
            ip = socket.gethostbyname(proxy)
        elif "HTTP_PROXY" in os.environ:
            proxy, port = os.environ['http_proxy'].strip('/').split('//')[1].split(':')
            ip = socket.gethostbyname(proxy)

        if proxy:
            print ' You are using proxy: ' + ctext('%s:%s' % (proxy, port), 'pB')
            useit = 'yes' if raw_input(
                ctext(' Use this proxy? ', 'B') + '([yes]|no):') in 'yes' else 'no'

        if useit == 'no':
            print ' Input your http proxy such as ' + ctext('www.abc.com:8080', 'pB')
            while 1:
                try:
                    proxy, port = raw_input(' Your\033[95m proxy:port \033[0m: ').split(':')
                    ip = socket.gethostbyname(proxy)
                    port = port.strip()
                    if not 0 <= int(port) <= 65535:
                        raise ValueError
                except ValueError:
                    print ctext(' Error: Http proxy must in format ', 'r') + ctext('address:port', 'B')
                    print ' Where ' + ctext('address', 'B') + ' is in form of www.abc.com or 123.321.4.5'
                    print '       ' + ctext('port', 'B') + ' is a number in range 0-65535'
                else:
                    break
        cfg.proxy['address'] = proxy
        cfg.proxy['port'] = port
        cfg.proxy['ip'] = ip

    get_input(cfg, 'config')
    print '\n' + '_' * 12 + ctext(' Config done', 'gB') + '_' * 12 + '\n'


if not os.path.exists("config.ini"):
    os.symlink(config_file, "config.ini")

if not os.path.exists("user_script.sh"):
    call(["cp", "user_script.sh.tmp", user_script_file])
    os.symlink(user_script_file, "user_script.sh")

# ------------------- check_dependencies: ----------------------
mirrors.extend(cfg.mirror['url'].split(', '))
use_proxy, proxy, port, ip = cfg.proxy.values()
sort_by = cfg.sort.values()[0]
s_country, s_port, s_score = cfg.filter.values()
dns_fix, dns = cfg.dns.values()
verbose = cfg.openvpn.values()[0]

required = {'openvpn': 0, 'python-requests': 0}

try:
    import requests
except ImportError:
    required['python-requests'] = 1

if not os.path.exists('/usr/sbin/openvpn'):
    required['openvpn'] = 1

need = [p for p in required if required[p]]
if need:
    print ctext('\n**Lack of dependencies**', 'rB')
    env = dict(os.environ)
    env['http_proxy'] = 'http://' + proxy + ':' + port
    env['https_proxy'] = 'http://' + proxy + ':' + port

    for package in need:
        print '\n___Now installing', ctext(package, 'gB')
        print
        call([pkg_mgr, '-y', 'install', package], env=env)

    import requests


# -------- all dependencies should be available after this line ----------------------
dns_manager()
ranked, vpn_list = refresh_data()

labels = ['Idx', 'Geo', 'Ping', 'Speed', 'UpTime', 'Log', 'Score', 'proto', 'Ip', 'Port']
spaces = [5, 4, 5, 8, 12, 4, 8, 6, 16, 6]
labels = [label.center(spaces[ind]) for ind, label in enumerate(labels)]
connected_servers = []

while True:
    print ctext('Use proxy: ', 'B'), use_proxy,
    print ' || ', ctext('Country: ', 'B'), s_country,
    print ' || ', ctext('Min score: ', 'B'), s_score,
    print ' ||', ctext('Portal:', 'B'), s_port

    if not ranked:
        print '\nNo server found for "%s"\n' % s_country
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
            print ctext('Goodbye'.center(40), 'gB')
            sys.exit()
        elif user_input.strip().lower() in ('r', 'refresh'):
            ranked, vpn_list = refresh_data()
        elif user_input.strip().lower() in ('c', 'config'):
            get_input(cfg, [user_input])

            mirrors = ["http://www.vpngate.net"] + cfg.mirror['url'].split(', ')
            use_proxy, proxy, port, ip = cfg.proxy.values()
            sort_by = cfg.sort.values()[0]
            s_country, s_port, s_score = cfg.filter.values()
            dns_fix, dns = cfg.dns.values()
            verbose = cfg.openvpn.values()[0]

            ranked, vpn_list = refresh_data()
        elif re.findall(r'^\d+$', user_input.strip()) and int(user_input) < server_sum:
            chose = int(user_input)
            print time.ctime().center(40)
            print ('Connect to ' + vpn_list[ranked[chose]].country_long).center(40)
            print vpn_list[ranked[chose]].ip.center(40)
            connected_servers.append(vpn_list[ranked[chose]].ip)
            vpn_file = vpn_list[ranked[chose]].write_file()
            vpn_file.close()
            vpn_manager(os.path.abspath(vpn_file.name))
        else:
            print 'Invalid command!'
            print '  q(uit) to quit\n  r(efresh) to refresh table\n' \
                  '  c(onfig) to change setting\n  number in range 0~%s to choose vpn\n' % (server_sum - 1)
            time.sleep(3)

        if SIGTERM:
            print ctext('Goodbye'.center(40), 'gB')
            sys.exit()

    except KeyboardInterrupt:
        time.sleep(0.5)
        print "\n\nSelect another VPN server or 'q' to quit"
