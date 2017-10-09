#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"

import os, sys
import signal
import socketserver
import time
import re
import traceback
from io import StringIO
from fcntl import fcntl, F_GETFL, F_SETFL
from subprocess import call, run, Popen, PIPE, STDOUT
from base import Setting, FavoriteSevers, is_IF_ok
from fetcher import Fetcher
from threading import Timer
from traceback import print_tb

# merge the output stream for log into 1 file
sys.stderr = sys.stdout

class MyTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # self.request is the TCP socket connected to the client
        UI_data = self.request.recv(1024).strip()
        UI_sock = self.request

        # this run in a thread so we must catch the error again
        try:
            callback(UI_data, UI_sock)
        except Exception as e:
            buff = StringIO()
            traceback.print_tb(e.__traceback__, file=buff)
            buff.seek(0)
            for line in buff:
                my_vpn_manager.logger(b'ERROR' + line.encode())
            else:
                del buff
                my_vpn_manager.logger(b'ERROR  ' + repr(e).encode())
        finally:
            UI_sock.close()


class VpnManager:
    def __init__(self):
        self.my_config = Setting()
        self.my_config.load()
        self.ipv6_status = int(run('cat /proc/sys/net/ipv6/conf/all/disable_ipv6'.split(), stdout=PIPE).stdout.strip())

        # vpn servers data
        self.fetcher = Fetcher(self.logger)
        self.servers_data = (None, None)                    # hold (sorted list, vpn_dict)
        self.my_favorites = FavoriteSevers()                # hold list of saved server
        self.mode = self.my_config.network['mode']          # main | favorite
        self.current_server = None
        self.past_servers = []

        # get current cursor position of the log file
        # updated everytime a new vpn connection is make
        # or after fetching server's data complete
        self.today = time.strftime("%Y%m%d")
        self.log = open("logs/vpn_{}.log".format(self.today), "ab")     # no need buffering=0, the logger() will flush
        self.new_ftell = self.log.seek(0, 2)

        self.verbose = self.my_config.show_log['verbose']
        self.exit = False

        # connection control
        self.max_retry = 3
        self.dropped_time = 0
        self.ovpn_process = None
        self.isConnecting = False

        # automation control
        self.is_on_duty = False
        self.selected_index = -1
        self.next_refresh_time = 0
        self.refresh_status = 0             # 0|1|2 = unknown | refreshing | finished

        #
        self.dns_orig = '/etc/resolv.conf.bak'
        self.dns = ''

        # communicating channel
        self.host = 'localhost'
        self.port = 0   # 0:random available port
        self.communicator = socketserver.TCPServer((self.host, self.port), MyTCPHandler)
        self.port = self.communicator.server_address[1]     # get the real port
        self.connected_vpn = ''

        # detach from current terminal
        ref = os.fork()
        if ref:
            sys.exit()
        os.setsid()     # stop receiving any control signal from original terminal, go daemon

        self.communicator.allow_reuse_address = True
        self.communicator.timeout = 0.1
        self.channel = None
        self.recv = ''
        self.time_interval = 0.5  # second

    def refresh_data(self, dont_care=True):
        # prevent multiple calling at the same time
        if self.refresh_status == 1:
            return
        else:
            self.refresh_status = 1

        self.servers_data = self.fetcher.fetch_data()
        self.next_refresh_time = time.time() + float(self.my_config.automation["fetch_interval"]) * 3600
        self.new_ftell = self.log.tell()
        self.selected_index = -1

        if dont_care:
            self.refresh_status = 0
        else:
            self.refresh_status = 2

    def dns_manager(self, action='backup'):
        network = self.my_config.network
        dns_fix = network['fix_dns']

        if not os.path.exists(self.dns_orig):
            self.logger(b'Backup DNS setting\n')
            backup = ['-aL', '/etc/resolv.conf', '/etc/resolv.conf.bak']
            call(['cp'] + backup)

        if action == "change" and dns_fix == 'yes':
            DNS = network['dns']
            DNS = DNS.replace(' ', '').split(',')

            with open('/etc/resolv.conf', 'w+') as resolv:
                for dns in DNS:
                    resolv.write('nameserver ' + dns + '\n')
            self.logger(b'Changed DNS')

        elif action == "restore":
            self.logger(b'Restored DNS')
            reverse_DNS = ['-a', '/etc/resolv.conf.bak', '/etc/resolv.conf']
            call(['cp'] + reverse_DNS)

    def post_action(self, when):
        """ Change DNS, and do additional behaviors defined by user in user_script.sh"""
        if when == 'up':
            self.dns_manager(action='change')

            # call user_script
            up = ('bash %s up' % self.my_config.user_script_file).split()
            results = run(up, stderr=PIPE, stdout=PIPE)

        elif when == 'down':
            self.dns_manager('restore')

            # call user_script
            down = ('bash %s down' % self.my_config.user_script_file).split()
            results = run(down, stderr=PIPE, stdout=PIPE)

        if results.stdout:
            res = results.stdout
            self.logger(res, b'[user script]')
        if results.returncode:
            err = results.stderr
            self.logger(err, b'[user script]')

        # print('external call returned')
        self.logger(bytes("Post action %s done" % when, 'ascii'))
        self.self_status()

    def vpn_connect(self, idx_num):
        self.selected_index = idx_num

        if self.isConnecting:
            self.vpn_terminate(False)

        self.my_config.load()  # reflect any change if it is

        if self.mode == 'main':
            sorted_vpn, vpn_dict = self.servers_data
            self.current_server = vpn_dict[sorted_vpn[idx_num]]
        else:  # mode favorite
            self.current_server = self.my_favorites[idx_num]

        self.connected_vpn = "%s " % idx_num + str(self.current_server)
        # ensure the ip is always at the bottom of the list
        if self.current_server.ip in self.past_servers:
            self.past_servers.remove(self.current_server.ip)
        self.past_servers.append(self.current_server.ip)

        vpn_file = self.current_server.write_file()
        vpn_file.close()

        command = ['openvpn', '--config', os.path.abspath(vpn_file.name)]
        self.ovpn_process = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)

        # get current p.stdout flags
        flags = fcntl(self.ovpn_process.stdout, F_GETFL)

        # make it become non-blocking when reading
        fcntl(self.ovpn_process.stdout, F_SETFL, flags | os.O_NONBLOCK)
        self.isConnecting = True

        self.new_ftell = self.log.tell()

    def vpn_terminate(self, is_broken=True, is_dead=False):
        if not is_dead:
            self.ovpn_process.send_signal(signal.SIGINT)
        else:
            self.logger(b'OpenVpn has self-terminated or been killed by outside signal!\n')

        self.ovpn_process.wait()
        for line in self.ovpn_process.stdout:
            self.logger(line, source=b'[OpenVpn]')

        self.logger(b'VPN tunnel is terminated\n')
        self.isConnecting = False
        self.connected_vpn = ''
        self.post_action('down')
        if is_broken:
            self.logger(b'done')

    def signal_handler(self, signals, frame):
        self.logger(b"Signal received: "+bytes(repr(signals), "ascii"))

        if signals == signal.SIGALRM:
            self.logger(b"Clean logs older than 3 days")
            all_logs = re.findall(r"vpn_\d{8}.log", ''.join(os.listdir("logs")))
            for log in all_logs:
                path = "logs/"+log
                if int(time.strftime("%Y%m%d")) - int(log[-12:-4]) >= 3:
                    os.remove(path)

            # do it again after
            signal.alarm(24 * 60 * 60)
            return
        else:
            # exit at SIGINT, SIGTERM, whatever
            self.exit = True

    def handle_request(self, cmd, channel=None):
        #
        self.logger(cmd, source=b'[UI]')
        if b'connect' in cmd:
            idx_num = int(cmd.split()[-1])
            self.vpn_connect(idx_num)

        elif cmd == b'stop':
            if self.isConnecting:
                self.vpn_terminate()

            self.my_config.automation['activate'] = 'no'
            self.logger(b'Automation temporarily off: UI said STOP')

        elif cmd == b'next':
            l = len(self.servers_data[0])-1 if self.servers_data[0] else len(self.my_favorites)
            if self.selected_index < l:
                self.vpn_connect(self.selected_index + 1)
                channel.sendall(b'1')
            else:
                channel.sendall(b'0')

        elif cmd == b'prev':
            l = len(self.servers_data[0]) - 1 if self.servers_data[0] else len(self.my_favorites)
            if self.selected_index > 0:
                self.vpn_connect(self.selected_index - 1)
                channel.sendall(b'1')
            else:
                channel.sendall(b'0')

        elif cmd == b'change dns':
            self.dns_manager('change')
        elif cmd == b'restore dns':
            self.dns_manager('restore')

        elif cmd == b'status':
            if self.isConnecting:
                data = "1 %s" % self.connected_vpn
            else:
                data = "0"
            channel.sendall(data.encode())

        elif cmd == b'exit':
            self.exit = True

        elif cmd == b'ftell':
            channel.sendall(str(self.new_ftell).encode())

        elif cmd == b'refresh':
            self.refresh_data()

        elif cmd in [b'auto off', b'aoff']:
            self.my_config.automation['activate'] = 'no'
            self.my_config.write()
        elif cmd in [b'auto on', b'aon']:
            self.my_config.automation['activate'] = 'yes'
            self.my_config.write()

        elif cmd in [b'add fav', b'save']:
            # print(self.current_server)
            self.my_favorites.add(self.current_server)
        elif b'remove' in cmd:
            if self.mode != 'favorite':
                self.logger(b'This action is only valid in favorite mode')
                return
            else:
                idx = list(map(int, cmd.split()[1:]))
                self.my_favorites.remove(idx)

        elif cmd == b'mode main':
            self.mode = 'main'
            self.my_config.network['mode'] = 'main'
            self.my_config.write()
        elif cmd in [b'mode fav', b'mode favorite']:
            self.mode = 'favorite'
            self.my_config.network['mode'] = 'favorite'
            self.my_config.write()
        elif cmd in [b'alive', b'check', b'check alive']:
            if self.mode != 'favorite':
                self.logger(b'This action is only valid in favorite mode')
                return
            else:
                favorite_dict = self.my_favorites.dict
                self.fetcher.reload_setting()
                self.fetcher._probe(favorite_dict)
                alive_idx = [str(idx) for idx, x in enumerate(self.my_favorites) if x.name in favorite_dict]
                self.logger(f"fav alive = {' '.join(alive_idx)}".encode())

    def log_open(self):
        """ Open the log of today"""

        today = time.strftime("%Y%m%d")
        if today != self.today:
            self.log.write(b"___ go to the next day ___\n")
            self.today = today
            self.log.close()

            output = "logs/vpn_{}.log".format(today)
            self.log = open(output, "ab")
            self.new_ftell = 0

    def logger(self, msg: bytes, source: bytes = b'[vpn manager]'):
        if source == b'[OpenVpn]':
            time_stamp = msg[11:19]
            msg = msg[25:]
        else:
            time_stamp = time.strftime("%H:%M:%S").encode()

        msg = b"%s %s %s" % (time_stamp, source, msg)
        if msg[-1] != 10:
            msg += b'\n'

        self.log_open()
        self.log.write(msg)
        self.log.flush()

    def automate(self):
        if not is_IF_ok():
            return

        if not self.isConnecting:
            if not self.is_on_duty:
                self.is_on_duty = True
                # try to connect to the next server
                self.logger(b'___ Automation entry point: auto connect ___')

            if self.my_config.network['mode'] == 'main':
                if self.refresh_status == 0:
                    if not self.servers_data[0]:
                        # spam a thread so that main loop is not locked up
                        Timer(0.1, self.refresh_data, args=[False]).start()
                        time.sleep(1)
                    else:
                        self.selected_index += 1
                        if self.selected_index >= len(self.servers_data[0]):
                            # current server list has run out, trigger the refresh on the next loop
                            self.servers_data = (None, None)
                        else:
                            self.logger(b'Start new connection')
                            self.vpn_connect(self.selected_index)
                            self.is_on_duty = False

                elif self.refresh_status == 2:
                    self.refresh_status = 0
                    if not self.servers_data[0]:
                        # temporarily turn off automation
                        self.my_config.automation['activate'] = 'no'
                        self.logger(b'Automation temporarily off: No data to work with!')
                        self.is_on_duty = False

            else:  # favorite list
                self.selected_index += 1
                if self.selected_index >= len(self.my_favorites):
                    print(len(self.my_favorites))
                    # the favorite list has run out, change mode to 'main'
                    # and go to the next loop
                    self.logger(b'Favorite list exceeded! Switch to main list.')
                    self.mode = self.my_config.network['mode'] = 'main'
                    self.my_config.write()      # should we keep user setting or prior to be able to connect?
                else:
                    self.logger(b'Start new connection')
                    self.vpn_connect(self.selected_index)
                    self.is_on_duty = False

        # self refreshing the data
        elif self.my_config.automation["fetch_interval"] >= "0.5":
            if time.time() >= self.next_refresh_time and self.refresh_status == 0:
                self.logger(b'___ Automation entry point: auto refresh data ___')
                # spam a thread so that main loop is not locked up
                Timer(0.1, self.refresh_data).start()
                time.sleep(1)

    def loop(self):
        msg = "=> service has started at {}:{}\n".format(self.host, self.port).encode()
        self.logger(msg)
        self.self_status()

        while 1:
            # check for commands from the outside
            self.communicator.handle_request()

            # check our connection if it is active
            if self.isConnecting:
                p = self.ovpn_process
                line = p.stdout.readline()

                # loop until there is nothing else to print
                while line:
                    if self.verbose == 'yes':
                        self.logger(line, source=b'[OpenVpn]')
                    if b'Initialization Sequence Completed' in line:
                        self.dropped_time = 0
                        self.post_action('up')
                        self.logger(b'VPN tunnel established successfully\n')
                        self.logger(b'done\n')
                    elif b'Restart pause, ' in line and self.dropped_time <= self.max_retry:
                        self.dropped_time += 1
                        self.logger(('Vpn has restarted %s time\n' % self.dropped_time).encode('ascii'))
                    elif self.dropped_time == self.max_retry or \
                                    any(errmsg in line for errmsg in [b'Connection timed out',
                                                                      b'Cannot resolve',
                                                                      b'No route to host',
                                                                      b'Network is unreachable']):
                        self.dropped_time = 0
                        self.logger(b'Terminate vpn\n')
                        self.vpn_terminate()

                    line = p.stdout.readline()
                    time.sleep(0.05)

                if not p.poll() is None and self.isConnecting:
                    # terminated by outside signal
                    self.vpn_terminate(is_dead=True)

            # automation
            if self.my_config.automation['activate'] == 'yes':
                self.automate()

            if self.exit:
                # clean up
                if self.isConnecting:
                    self.my_config.automation["activate"] = "no"
                    self.vpn_terminate()
                else:
                    self.communicator.server_close()
                    self.logger(b'Exit')
                    self.logger(b'-'*80)
                    self.self_status()
                    try:
                        # because the manager loses the server_dict on exit,
                        # so data has no meaning
                        os.remove("data.txt")
                    except FileNotFoundError:
                        pass

                    break

            time.sleep(self.time_interval)

        # finishing action
        self.log.close()

    def self_status(self):
        template = "{}\n" \
                   "pid:{}\n" \
                   "host:{}\n"\
                   "port:{}\n" \
                   "vpn:{}\n"

        with open("logs/manager.log", "w+") as status:
            if self.exit:
                stat = template.format(0,'','','','')
                self.past_servers = []
            else:
                stat = template.format(1,os.getpid(), self.host, self.port, self.connected_vpn)

            status.write(stat)
            status.write('\n'.join(self.past_servers))

if __name__ == '__main__':
    my_vpn_manager = VpnManager()
    signal.signal(signal.SIGINT, my_vpn_manager.signal_handler)
    signal.signal(signal.SIGTERM, my_vpn_manager.signal_handler)

    # schedule for deleting old log files
    signal.signal(signal.SIGALRM, my_vpn_manager.signal_handler)
    my_vpn_manager.signal_handler(signal.SIGALRM, 0)
    signal.alarm(24*60*60)

    callback = my_vpn_manager.handle_request
    print("vpn manager has started")
    try:
        my_vpn_manager.loop()
    except Exception as e:
        buff = StringIO()
        traceback.print_tb(e.__traceback__, file=buff)
        buff.seek(0)
        for line in buff:
            my_vpn_manager.logger(b'ERROR' + line.encode())
        else:
            my_vpn_manager.logger(b'ERROR  ' + repr(e).encode())
    finally:
        my_vpn_manager.log.close()