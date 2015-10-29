#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"
__copyright__ = "Copyright 2015+, duc_tin"
__license__ = "GPLv2"
__version__ = "1.1"
__maintainer__ = "duc_tin"
__email__ = "nguyenbaduc.tin@gmail.com"

import os
import signal
import base64
import time
import datetime
from copy import deepcopy
from config import *
from subprocess import call, Popen, PIPE
from threading import Thread
from Queue import Queue, Empty
from collections import deque, OrderedDict


# Get sudo privilege
euid = os.geteuid()
if euid != 0:
    args = ['sudo', sys.executable] + sys.argv + [os.environ]
    os.execlpe('sudo', *args)

# Threading
ON_POSIX = 'posix' in sys.builtin_module_names

# Define some mirrors of vpngate.net
mirrors = ['http://www.vpngate.net',
           'http://103.253.112.16:49882',
           'http://158.ip-37-187-34.eu:58272',
           'http://121.186.216.97:38438',
           'http://hannan.postech.ac.kr:6395',
           'http://115.160.46.181:38061',
           'http://hornet.knu.ac.kr:36171',
           'http://182-166-242-138f1.osk3.eonet.ne.jp:64298']

# TODO: add user manual to this and can be access by h, help. It may never be done, reads the README file instead


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
        self.logPolicy = data[11]
        self.config_data = base64.b64decode(data[-1])
        self.proto = 'tcp' if '\r\nproto tcp\r\n' in self.config_data else 'udp'

    def write_file(self, use_proxy='no', proxy=None, port=None):
        txt_data = self.config_data
        if use_proxy == 'yes':
            txt_data = txt_data.replace('\r\n;http-proxy-retry\r\n', '\r\nhttp-proxy-retry 3\r\n')
            txt_data = txt_data.replace('\r\n;http-proxy [proxy server] [proxy port]\r\n',
                                        '\r\nhttp-proxy %s %s\r\n' % (proxy, port))

        tmp_vpn = open('vpn_tmp', 'w+')
        tmp_vpn.write(txt_data)
        return tmp_vpn

    def __str__(self):
        spaces = [6, 7, 6, 10, 10, 10, 10, 8]
        speed = self.speed / 1000. ** 2
        uptime = datetime.timedelta(milliseconds=int(self.uptime))
        uptime = re.split(',|\.', str(uptime))[0]
        txt = [self.country_short, str(self.ping), '%.2f' % speed, uptime, self.logPolicy, str(self.score), self.proto]
        txt = [dta.center(spaces[ind + 1]) for ind, dta in enumerate(txt)]
        return ''.join(txt)


class Connection:
    def __init__(self):
        self.path = os.path.realpath(sys.argv[0])
        self.config_file = os.path.split(self.path)[0] + '/config.ini'
        self.args = sys.argv[1:]
        self.debug = []

        self.vpndict = {}
        self.sorted = []

        self.vpn_process = None
        self.vpn_queue = None
        self.connect_status = False
        self.kill = False

        self.connected_servers = []
        self.messages = OrderedDict([('country', deque([' '], maxlen=1)),
                                     ('status', deque([' ', ' '], maxlen=2)),
                                     ('debug', deque(maxlen=20))])

        # get proxy from config file
        if not os.path.exists(self.config_file):
            self.first_config()
        if len(self.args):
            # process commandline arguments
            if self.args[0] in ['r', 'restore']:
                self.dns_manager('restore')
            else:
                get_input(self.config_file, self.args)

        self.configs = read_config(self.config_file)
        self.proxy, self.port, self.ip = self.configs[0:3]
        self.sort_by = self.configs[3]
        self.use_proxy = self.configs[4]
        self.country = self.configs[5]
        self.dns_fix = self.configs[6]
        self.dns = self.configs[7]
        self.verbose = self.configs[8]

    def first_config(self):
        print '\n' + '_'*12 + ctext(' First time config ', 'gB') + '_'*12 + '\n'
        print "If you don't know what to do, just press Enter to use default option\n"
        use_proxy = 'no' if raw_input(ctext('Do you need proxy to connect? ', 'B')+'[yes|no(default)]:') in 'no' else 'yes'
        if use_proxy == 'yes':
            print ' Input your http proxy such as ' + ctext('www.abc.com:8080', 'pB')
            while 1:
                try:
                    proxy, port = raw_input(' Your\033[95m proxy:port \033[0m: ').split(':')
                    ip = socket.gethostbyname(proxy)
                    port = port.strip()
                    if not 0 <= int(port) <= 65535:
                        raise ValueError
                except ValueError:
                    print ctext(' Error: Http proxy must in format ', 'r')+ctext('address:port', 'B')
                    print ' Where ' + ctext('address', 'B') + ' is in form of www.abc.com or 123.321.4.5'
                    print '       ' + ctext('port', 'B') + ' is a number in range 0-65535'
                else:
                    break

        else:
            proxy, port, ip = '', '', ''

        sort_by = raw_input(ctext('\nSort servers by ', 'B') + '[speed (default) | ping | score | up time]: ')
        if sort_by not in ['speed', 'ping', 'score', 'up time']:
            sort_by = 'speed'

        country = raw_input(ctext('\nFilter server by country ','B') + '[eg: all (default), jp, japan]: ')
        if not country:
            country = 'all'

        dns_fix = 'yes' if raw_input(ctext('\nFix DNS leaking ', 'B') + '[yes (default) | no] : ') in 'yes' else 'no'
        dns = ''
        if dns_fix == 'yes':
            dns = raw_input(' DNS server or Enter to use 8.8.8.8 (google): ')
        if not dns:
            dns = '8.8.8.8, 84.200.69.80, 208.67.222.222'
        verbose = 'no' if 'n' in raw_input(ctext('Write openvpn log? [yes (default)| no]: ', 'B')) else 'yes'
        write_config(self.config_file, proxy, port, ip, sort_by, use_proxy, country, dns_fix, dns, verbose)
        print '\n' + '_'*12 + ctext(' Config done', 'gB') + '_'*12 + '\n'

    def get_data(self):
        if self.use_proxy == 'yes' and not self.connect_status:
            self.messages['debug'].appendleft(' Pinging proxy... ')
            ping_name = ['ping', '-w 2', '-c 2', '-W 2', self.proxy]
            ping_ip = ['ping', '-w 2', '-c 2', '-W 2', self.ip]
            res1, err1 = Popen(ping_name, stdout=PIPE, stderr=PIPE).communicate()
            res2, err2 = Popen(ping_ip, stdout=PIPE, stderr=PIPE).communicate()

            if err1 and not err2:
                self.messages['debug'][0] += '[failed]'
                self.messages['debug'].extendleft([" Warning: Cannot resolve proxy's hostname. Use last known IP"])
                self.proxy = self.ip
            elif err1 and err2:
                self.messages['debug'][0] += '[failed]'
                self.messages['debug'].appendleft('  Ping proxy got error: '+err1)
                self.messages['debug'].appendleft('  Check your proxy setting')
            elif not err1 and '100% packet loss' in res1:
                self.messages['debug'][0] += '[dead]'
                self.messages['debug'].appendleft(' Warning: Proxy not response to ping')
                self.messages['debug'].appendleft(" Either proxy's security does not allow it to response to "
                                                  "ping packet or proxy itself is dead")
            else:
                self.messages['debug'][0] += '[alive]'

            proxies = {
                'http': 'http://' + self.proxy + ':' + self.port,
                'https': 'http://' + self.proxy + ':' + self.port,
            }

        else:
            proxies = {}

        i = 0
        while i < len(mirrors):
            try:
                self.messages['debug'].appendleft(' using gate: '+mirrors[i])
                gate = mirrors[i] + '/api/iphone/'
                vpn_data = requests.get(gate, proxies=proxies, timeout=3).text.replace('\r', '')

                if 'vpn_servers' not in vpn_data:
                    raise requests.exceptions.RequestException

                servers = [line.split(',') for line in vpn_data.split('\n')]
                self.vpndict = {s[0]: Server(s) for s in servers[2:] if len(s) > 1}
                self.messages['debug'].appendleft(' Fetching servers completed')
                break

            except requests.exceptions.RequestException as e:
                self.messages['debug'].appendleft(str(e))
                self.messages['debug'].appendleft(' Connection to gate ' + mirrors[i] + ' failed')
                i += 1
        else:
            self.messages['debug'].appendleft(' Failed to get VPN servers data\n Check your network setting and proxy')
            sys.exit(1)

    def refresh_data(self):
        # fetch data from vpngate.net
        self.get_data()
        if self.country != 'all':
            self.vpndict = dict([vpn for vpn in self.vpndict.items()
                                if re.search(r'\b%s\b' % self.country, vpn[1].country_long.lower() + ' '
                                             + vpn[1].country_short.lower())])

        if self.sort_by == 'speed':
            sort = sorted(self.vpndict.keys(), key=lambda x: self.vpndict[x].speed, reverse=True)
        elif self.sort_by == 'ping':
            sort = sorted(self.vpndict.keys(), key=lambda x: self.vpndict[x].ping)
        elif self.sort_by == 'score':
            sort = sorted(self.vpndict.keys(), key=lambda x: self.vpndict[x].score, reverse=True)
        elif self.sort_by == 'up time':
            sort = sorted(self.vpndict.keys(), key=lambda x: int(self.vpndict[x].uptime))
        else:
            print '\nValueError: sort_by must be in "speed|ping|score|up time" but got "%s" instead.' % self.sort_by
            print 'Change your setting by "$ ./vpnproxy config"\n'
            sys.exit()

        self.sorted[:] = sort
        self.dns_manager()

    def dns_manager(self, action='backup'):
        dns_orig = '/etc/resolv.conf.bak'

        if not os.path.exists(dns_orig):
            print ctext('Backup DNS setting', 'yB')
            backup = ['-a', '/etc/resolv.conf', '/etc/resolv.conf.bak']
            call(['cp'] + backup)

        if action == "change" and self.dns_fix == 'yes':
            DNS = self.dns.replace(' ', '').split(',')

            with open('/etc/resolv.conf', 'w+') as resolv:
                for dns in DNS:
                    resolv.write('nameserver ' + dns + '\n')

        elif action == "restore":
            self.messages['status'][1] = 'Restore dns'
            reverseDNS = ['-a', '/etc/resolv.conf.bak', '/etc/resolv.conf']
            call(['cp'] + reverseDNS)

    @staticmethod
    def vpn_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    def vpn_connect(self, chosen):
        """
        Disconnect the current connection and spawn a new one
        """
        if self.connect_status:
            self.vpn_cleanup()

        server = self.vpndict[self.sorted[chosen]]
        self.messages['country'] += [server.country_long.strip('of')+' '+server.ip]
        self.connected_servers.append(server.ip)
        vpn_file = server.write_file(self.use_proxy, self.proxy, self.port)
        vpn_file.close()

        ovpn = vpn_file.name
        command = ['openvpn', '--config', ovpn]
        p = Popen(command, stdout=PIPE, stderr=PIPE, bufsize=1, close_fds=ON_POSIX)
        q = Queue()
        t = Thread(target=self.vpn_output, args=(p.stdout, q))
        t.daemon = True
        t.start()

        self.vpn_process = p
        self.vpn_queue = q

    def vpn_cleanup(self):
        p, q = self.vpn_process, self.vpn_queue
        if p.poll() is None:
            p.send_signal(signal.SIGINT)
            p.wait()
        self.connect_status = False
        self.dns_manager('restore')

    def kill_other(self):
        """
        Kill all openvpn processes no matter they are controlled by
        this program or not. Use when connection gets trouble
        """
        command = ['sudo', 'pkill', 'openvpn']
        call(command)
        self.messages['status'].appendleft(['All openvpn processes are terminated'])
        self.dns_manager('restore')

    def vpn_checker(self):
        """ Check VPN season
            If vpn tunnel break or fail to create, terminate vpn season
            So openvpn not keep sending requests to proxy server and
             save you from being blocked.
        """
        p, q = self.vpn_process, self.vpn_queue

        if self.kill and self.connect_status:
            self.kill = False
            self.vpn_cleanup()
            self.messages['status'] += ['VPN tunnel is terminated', '']
            self.messages['country'] += [' ', ' ']

        try:
            line = q.get_nowait()
        except Empty:
            return
        else:
            self.messages['debug'].appendleft(line.strip()[11:])
            if 'Initialization Sequence Completed' in line:
                self.dns_manager('change')
                self.messages['status'] += ['VPN tunnel established successfully', 'Ctrl+C to quit VPN']
                self.connect_status = True
            elif 'Restart pause, 5 second(s)' in line or 'Connection timed out' in line or 'SIGTERM[hard,]' in line:
                self.messages['status'] += ['Vpn got error, terminated', ' ']
                self.vpn_cleanup()
            elif 'ERROR' in line and 'add command failed' not in line or 'Exiting due' in line:
                self.messages['status'] += ['Vpn got error, exited', ' ']
                self.vpn_cleanup()

            elif p.poll() is None and not self.connect_status:
                self.messages['status'] += ['Connecting...', ' ']


class Display:
    def __init__(self, vpn_connection):
        """
        :type vpn_connection: Connection
        """
        self.ovpn = vpn_connection
        self.get_data = Thread(target=self.ovpn.refresh_data)
        self.get_data_status = 'finish'
        self.vpn_log = deque(maxlen=20)

        self.timer = 0
        self.cache_msg = None
        self.index = 0
        self.ser_no = 16
        self.data_ls = ['']
        self.debug = urwid.Text(u'')
        self.palette = [('command', 'dark green, bold', 'default'),
                        ('normal', 'default', 'default'),
                        ('focus', 'yellow', 'dark blue'),
                        ('failed', 'dark red', 'default'),
                        ('lost', 'dark red, bold', 'default'),
                        ('attention', 'default, bold', 'default'),
                        ('attention2', 'default, bold, blink', 'default'),
                        ('button', 'standout, bold', ''),
                        ('popbgs', 'white', 'dark blue')]

        signal.signal(signal.SIGINT, self.signal_handler)

        # Header
        self.sets = self.setting()  # Pile of MyColumn

        # Body
        self.Udata = []                 # used by make_GUI and update_GUI, just for ease of access
        self.table = self.make_GUI()  # list of lines, urwid.columns

        self.input = urwid.Edit(('command', u"Vpn command: "), edit_text=u'')
        self.clear_input = False
        urwid.connect_signal(self.input, 'change', self.input_handler)

        self.pages = urwid.Text([('command', 'page: '), '1/0'], align='center')
        self.cmd_row = urwid.Columns([self.input, self.pages])

        self.pile = urwid.Pile([self.debug] + self.table + [self.cmd_row])

        # Footer
        self.state = self.status()

        # Frame (Header, Body, Footer)
        self.Piles = MyPile([self.sets, self.pile, self.state], focus_item=1)
        fill = urwid.Filler(self.Piles, 'top')
        self.loop = urwid.MainLoop(fill, self.palette, unhandled_input=self.input_handler,
                                   pop_ups=True, handle_mouse=False)
        self.loop.set_alarm_in(sec=0.1, callback=self.periodic_checker)

    def get_vpn_data(self):
        del self.data_ls[:]

        for key in self.ovpn.sorted:
            self.data_ls.append(str(self.ovpn.vpndict[key]))
        self.update_GUI()

    def periodic_checker(self, loop, user_data=None):
        loop.set_alarm_in(sec=0.1, callback=self.periodic_checker)

        # check if user want to kill vpn
        if self.ovpn.vpn_process:
            self.ovpn.vpn_checker()

        # check if user want to fetch new vpn server list
        if self.get_data_status == 'call' and not self.get_data.isAlive():
            self.get_vpn_data()     # clear the template of server list
            self.get_data = Thread(target=self.ovpn.refresh_data)
            self.get_data.daemon = True
            self.get_data.start()
            self.get_data_status = 'wait'
        elif self.get_data_status == 'wait' and not self.get_data.isAlive():
            self.get_vpn_data()
            self.get_data_status = 'finish'

        if self.clear_input:
            self.input.set_edit_text(self.clear_input[1])
            self.clear_input = False

        self.status(self.ovpn.messages)

    def signal_handler(self, signum, frame):
        self.ovpn.kill = True
        self.printf("Ctrl C is pressed. Press again or 'q' to quit program")
        if not self.ovpn.connect_status:
            raise urwid.ExitMainLoop()

    def input_handler(self, Edit, key_ls=None):
        # handle for self.input (Edit) on the fly
        if key_ls:
            if 'q' in key_ls or 'Q' in key_ls:
                self.exit(self.loop)
            if 'No such server!' == key_ls[:-1] or 'Invalid command!' == key_ls[:-1] or 'refresh' == key_ls[:-1]:
                self.clear_input = True, key_ls[-1]

        # handle for non alphabet key press
        elif isinstance(Edit, str):
            key = Edit
            if 'up' in key:
                self.index -= self.ser_no
                if self.index < 0 and len(self.data_ls) > self.ser_no:
                    self.index = len(self.data_ls) - len(self.data_ls) % self.ser_no
                elif self.index < 0:
                    self.index = 0
                self.update_GUI()
            elif 'down' in key:
                self.index += self.ser_no
                if self.index > len(self.data_ls):
                    self.index = 0
                self.update_GUI()
            elif key == 'esc':
                self.input.set_edit_text('')
            elif key == 'enter':
                self.printf('')
                text = self.input.get_edit_text().lower()
                if 'Invalid' in text:
                    self.input.set_edit_text('')

                elif text.isdigit():
                    chosen = int(text)
                    if chosen < len(self.data_ls):
                        self.index = (chosen // self.ser_no) * self.ser_no
                        self.ovpn.vpn_connect(chosen)
                        self.input.set_edit_text('')
                        self.update_GUI()
                    else:
                        self.input.set_edit_text('No such server!')
                        self.input.set_edit_pos(len(self.input.get_edit_text()))

                elif text.lower() in ['r', 'refresh']:
                    screen.get_data_status = 'call'
                    self.input.set_edit_text('')
                elif 'restore' in text:
                    self.ovpn.dns_manager('restore')
                    self.input.set_edit_text('')
                elif 'kill' in text:
                    self.ovpn.kill_other()
                    self.input.set_edit_text('')
                elif 'log' in text[:3]:
                    yn = self.ovpn.verbose
                    if 'on' in text[3:6]:
                        if yn == 'no': self.setting('f10')
                    elif 'off' in text[3:6]:
                        if yn == 'yes': self.setting('f10')
                    else:
                        self.ovpn.messages['debug'].appendleft(' Logging is currently ' + ('on' if yn == 'yes' else 'off'))
                        self.status(self.ovpn.messages)
                    self.input.set_edit_text('')

                else:
                    self.input.set_edit_text('Invalid command!')
                    self.input.set_edit_pos(len(self.input.get_edit_text()))

            elif key == 'ctrl f5':
                screen.get_data_status = 'call'
                self.input.set_edit_text('')
            elif key == 'ctrl r':
                self.ovpn.dns_manager('restore')
                self.input.set_edit_text('')
            elif key == 'ctrl k':
                self.ovpn.kill_other()
            elif len(key) > 1 and 'f' == key[0]:
                self.setting(key)
            else:
                pass

    @staticmethod
    def on_exit_clicked(button):
        raise urwid.ExitMainLoop()

    def printf(self, txt):
        self.debug.set_text(str(txt))

    def make_GUI(self):
        labels = ['Index', 'Country', 'Ping', 'Speed', 'Up time', 'Log Policy', 'Score', 'protocol']
        spaces = [5, 8, 6, 9, 10, 11, 9, 9]

        txt_labels = []
        for i, txt in enumerate(labels):
            tex = urwid.Text(txt, align='center')
            txt_labels.append(('fixed', spaces[i], tex))
        Ulabel = urwid.Columns(txt_labels)

        Udata = []      # temporary, different from self.Udata
        for i in range(self.ser_no):
            self.Udata.append(deepcopy(Ulabel))
            Udata.append(urwid.Padding(urwid.AttrMap(self.Udata[i], 'normal'), width=67))

        Ulabel = urwid.AttrMap(Ulabel, 'command')

        return [Ulabel] + Udata

    def update_GUI(self):
        data_list = self.data_ls

        # Page number
        total = str(len(data_list) // self.ser_no + 1)
        page_no = str(self.index/self.ser_no + 1)
        while page_no > total:
            self.index -= self.ser_no
            page_no = str(self.index/self.ser_no + 1)
        self.pages.set_text([('command', u'\u2191\u2193 page: '), page_no+'/'+total])

        # data for that page
        tmp_ls = data_list[self.index:self.index + self.ser_no]
        if len(tmp_ls) < self.ser_no:
            tmp_ls += [''] * (self.ser_no - len(tmp_ls))

        for i, line in enumerate(tmp_ls):
            ser_info = line.split() if line.split() else [''] * 7
            if len(ser_info) == 8:
                ser_info[3] += ' ' + ser_info.pop(4)
            tmp_index = str(self.index + i) if ser_info[0] else ''

            self.Udata[i].contents[0][0].set_text(tmp_index)
            for j, txt in enumerate(ser_info):
                self.Udata[i].contents[j+1][0].set_text(txt)

            # colorize connected item
            self.table[i + 1].original_widget.set_attr_map({None: None})
            if tmp_index and self.ovpn.connected_servers:
                vpn_name = self.ovpn.sorted[int(tmp_index)]
                ip = self.ovpn.vpndict[vpn_name].ip
                if ip == self.ovpn.connected_servers[-1]:
                    self.table[i + 1].original_widget.set_attr_map({None: 'focus'})
                elif ip in self.ovpn.connected_servers:
                    self.table[i + 1].original_widget.set_attr_map({None: 'failed'})

    def setting(self, key=None):
        proxy= self.ovpn.proxy
        port = self.ovpn.port
        ip   = self.ovpn.ip
        use_proxy = self.ovpn.use_proxy

        sort_by = self.ovpn.sort_by
        country = self.ovpn.country
        fix_dns = self.ovpn.dns_fix
        dns = self.ovpn.dns

        verbose = self.ovpn.verbose

        config_data = [use_proxy, fix_dns, country, sort_by]
        labels = ['Proxy: ', 'DNS fix: ', 'Country: ', 'Sort by: ']
        buttons = ['F2', 'F3', 'F4', 'F5']
        popup = [PopUpProxy, PopUpDNS, PopUpCountry, PopUpSortBy]
        param = [(use_proxy, proxy, port), (fix_dns, dns), country, sort_by]
        pop_size = [(0, 1, 39, 6), (0, 1, 35, 5), (0, 1, 25, 5), (7, 1, 12, 6)]

        if not key:
            txt_labels = []
            for i, txt in enumerate(labels):
                tex = MyText([('button', buttons[i]), ('attention', txt), config_data[i]])
                thing_with_popup = AddPopUp(tex, popup[i], value=param[i], trigger=buttons[i].lower(), size=pop_size[i])
                urwid.connect_signal(thing_with_popup, 'done', lambda button, k: self.setting(k))
                txt_labels.append(thing_with_popup)
            row1 = MyColumn(txt_labels[0:4])

            return row1

        else:
            self.Piles.focus_position = 1
            index = int(key[1:]) - 2

            if key == 'f2':
                yn = self.sets.contents[index][0].result[0]
                proxy, port = self.sets.contents[index][0].result[1:]

                use_proxy = self.ovpn.use_proxy = config_data[index] = yn
                self.ovpn.proxy, self.ovpn.port = proxy, port

                tex = [('button', buttons[index]), ('attention', labels[index]), config_data[index]]
                self.sets[index].set_text(tex)

            elif key == 'f3':
                yn = self.sets.contents[index][0].result[0]
                dns = self.ovpn.dns = self.sets.contents[index][0].result[1]

                fix_dns = self.ovpn.dns_fix = config_data[index] = yn

                tex = [('button', buttons[index]), ('attention', labels[index]), config_data[index]]
                self.sets[index].set_text(tex)

            elif key == 'f4':
                country = self.ovpn.country = config_data[index] = self.sets.contents[index][0].result
                tex = [('button', buttons[index]), ('attention', labels[index]), config_data[index]]
                self.sets[index].set_text(tex)
                self.input.set_edit_text('refresh')
                self.input.set_edit_pos(len('refresh'))

            elif key == 'f5':
                sort_by = self.ovpn.sort_by = config_data[index] = self.sets.contents[index][0].result
                tex = [('button', buttons[index]), ('attention', labels[index]), config_data[index]]
                self.sets[index].set_text(tex)
                self.input.set_edit_text('refresh')
                self.input.set_edit_pos(len('refresh'))

            elif key == 'f10':
                yn = self.ovpn.verbose
                verbose = self.ovpn.verbose = 'no' if yn == 'yes' else 'yes'
                self.ovpn.messages['debug'].appendleft(time.asctime() +
                                                       ': Logging is turned ' + ('off' if yn == 'yes' else 'on'))
                self.status(self.ovpn.messages)

            elif key == 'f7':
                pass

            config_path = self.ovpn.config_file
            write_config(config_path, proxy, port, ip, sort_by, use_proxy, country, fix_dns, dns, verbose)

    def status(self, msg=None):
        self.logger(msg)
        if msg:
            # self.printf(str(msg))
            ind = 0
            for mtype in msg:
                for m in msg[mtype]:
                    if 'successfully' in m or 'dns' in m or 'complete' in m:
                        self.state[ind].set_text(('attention', m))
                    elif 'got error' in m:
                        self.state[ind].set_text(('lost', m))
                    elif 'Connecting' in m:
                        self.state[ind].set_text(('attention2', m))
                    else:
                        self.state[ind].set_text(('normal', m))

                    ind += 1
            return

        message = [urwid.Text(u' ', align='center') for i in range(3)]
        debug_mes = [urwid.Text(u' ') for i in range(20)]
        return urwid.Pile(message + debug_mes)

    def logger(self, msg):
        if self.ovpn.verbose == 'no':
            return

        logpath = self.ovpn.config_file[:-10]+'vpn.log'
        if not msg:
            with open(logpath, 'w+') as log:
                log.writelines(['-'*40+'\n', time.asctime()+': Vpngate with proxy is started\n'])

        else:
            with open(logpath, 'a+') as log:
                if msg['debug'] != self.vpn_log and ' Pinging proxy... ' not in msg['debug']:
                    ind = 0
                    m = msg['debug'][ind]
                    if self.vpn_log:
                        while m != self.vpn_log[0]:
                            ind += 1
                            m = msg['debug'][ind]
                        while ind > 0:
                            ind -= 1
                            m = msg['debug'][ind]
                            self.vpn_log.appendleft(m)
                            log.write(m+'\n')
                    else:
                        for m in list(msg['debug'])[::-1]:
                            self.vpn_log.appendleft(m)
                            log.write(m+'\n')

    def run(self):
        self.loop.run()

    def exit(self,loop, data=None):
        loop.set_alarm_in(sec=0.2, callback=self.exit)
        if not self.ovpn.vpn_process or self.ovpn.vpn_process.poll() is not None:
            raise urwid.ExitMainLoop()
        else:
            self.ovpn.kill = True


# ------------------------- Main  -----------------------------------
vpn_connect = Connection()  # initiate network parameter

# ------------------- check_dependencies: ---------------------------
required = {'openvpn': 0, 'python-requests': 0, 'python-urwid': 0}
for module in ['requests', 'urwid']:
    try:
        __import__(module, globals(), locals(), [], -1)
    except ImportError:
        required['python-'+module] = 1

if not os.path.exists('/usr/sbin/openvpn'):
    required['openvpn'] = 1

need = [p for p in required if required[p]]
if need:
    print ctext('\n**Lack of dependencies**', 'rB')
    env = dict(os.environ)
    if vpn_connect.use_proxy == 'yes':
        env['http_proxy'] = 'http://' + vpn_connect.proxy + ':' + vpn_connect.port
        env['https_proxy'] = 'http://' + vpn_connect.proxy + ':' + vpn_connect.port

    for package in need:
        print '\n___Now installing', ctext(package, 'gB')
        print
        call(['apt-get', 'install', package], env=env)

    raw_input(ctext('  Done!\n  Press Enter to continue', 'g'))

import requests
from ui_elements import *

# -------- all dependencies should be available after this line --------

screen = Display(vpn_connect)
screen.get_data_status = 'call'
screen.run()
