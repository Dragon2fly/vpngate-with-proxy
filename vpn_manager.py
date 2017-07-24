#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"

import os, sys
import signal
import socketserver
import time
import re
from fcntl import fcntl, F_GETFL, F_SETFL
from subprocess import call, run, Popen, PIPE
from base import Setting
from fetcher import Fetcher


class MyTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # self.request is the TCP socket connected to the client
        UI_data = self.request.recv(1024).strip()
        UI_sock = self.request
        callback(UI_data, UI_sock)
        UI_sock.close()


class VpnManager:
    def __init__(self):
        self.my_config = Setting()
        self.my_config.load()

        # vpn servers data
        self.fetcher = Fetcher(self.logger)
        self.servers_data = (None, None)        # hold (sorted list, vpn_dict)

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
        self.selected_index = -1
        self.next_refresh_time = 0

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
        os.setsid()     # stop receiving any control signal from original terminal

        self.communicator.allow_reuse_address = True
        self.communicator.timeout = 0.1
        self.channel = None
        self.recv = ''
        self.time_interval = 0.3  # second

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
            self.vpn_terminate()

        self.my_config.load()  # reflect any change if it is

        sorted_vpn, vpn_dict = self.servers_data
        vpn_server = vpn_dict[sorted_vpn[idx_num]]
        self.connected_vpn = "%s " % idx_num + str(vpn_server)

        vpn_file = vpn_server.write_file()
        vpn_file.close()

        command = ['openvpn', '--config', os.path.abspath(vpn_file.name)]
        self.ovpn_process = Popen(command, stdout=PIPE, stdin=PIPE)

        # get current p.stdout flags
        flags = fcntl(self.ovpn_process.stdout, F_GETFL)

        # make it become non-blocking when reading
        fcntl(self.ovpn_process.stdout, F_SETFL, flags | os.O_NONBLOCK)
        self.isConnecting = True

        self.new_ftell = self.log.tell()

    def signal_handler(self, signals, frame):
        self.logger(b"Signal received: "+bytes(repr(signals), "ascii"))

        if signals == signal.SIGALRM:
            self.logger(b"Clean logs older than 3 days")
            all_logs = re.findall(r"vpn_\d{8}.log", ''.join(os.listdir("logs")))
            for log in all_logs:
                path = "logs/"+log
                if (time.time() - os.path.getmtime(path)) / 86400 > 3:
                    os.remove(path)
            return
        else:
            # exit at SIGINT, SIGTERM, whatever
            self.exit = True

    def vpn_terminate(self):
        self.ovpn_process.send_signal(signal.SIGINT)
        self.ovpn_process.wait()
        self.logger(b'VPN tunnel is terminated\n')
        self.isConnecting = False
        self.connected_vpn = ''
        self.post_action('down')

    def handle_request(self, cmd, channel):
        self.logger(cmd, source=b'[UI]')
        # print(cmd)
        if b'connect' in cmd:
            idx_num = int(cmd.split()[-1])
            self.vpn_connect(idx_num)

        elif cmd == b'stop':
            if self.isConnecting:
                self.vpn_terminate()

            self.my_config.automation['activate'] = 'no'
            self.logger(b'Automation temporarily off: UI said STOP')

        elif cmd == b'next':
            if self.selected_index < len(self.servers_data[0])-1:
                self.vpn_connect(self.selected_index + 1)
                channel.sendall(b'1')
            else:
                channel.sendall(b'0')
        elif cmd == b'prev':
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
            self.servers_data = self.fetcher.fetch_data()
            self.next_refresh_time = time.time() + float(self.my_config.automation["fetch_interval"]) * 3600
            self.new_ftell = self.log.tell()

        elif cmd == b'auto off':
            self.my_config.automation['activate'] = 'no'
            self.my_config.write()
        elif cmd == b'auto on':
            self.my_config.automation['activate'] = 'yes'
            self.my_config.write()

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

    def loop(self):
        msg = "service has started at {}:{}\n".format(self.host, self.port).encode('ascii')
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
                        self.logger(b'Ctrl+C to quit VPN\n')
                    elif b'Restart pause, ' in line and self.dropped_time <= self.max_retry:
                        self.dropped_time += 1
                        self.logger(('Vpn has restarted %s time\n' % self.dropped_time).encode('ascii'))
                    elif self.dropped_time == self.max_retry or \
                                    b'Connection timed out' in line or \
                                    b'Cannot resolve' in line:
                        self.dropped_time = 0
                        self.logger(line)
                        self.logger(b'Terminate vpn\n')
                        self.vpn_terminate()

                    line = p.stdout.readline()
                    time.sleep(0.05)

            # automation
            if self.my_config.automation['activate'] == 'yes':
                if not self.isConnecting:
                    # try to connect to the next server
                    self.logger(b'___ Automation entry point ___')
                    if not self.servers_data[0]:
                        self.servers_data = self.fetcher.fetch_data()
                        self.next_refresh_time = time.time() + float(self.my_config.automation["fetch_interval"]) * 3600

                    if not self.servers_data[0]:
                        # temporarily turn off automation
                        self.my_config.automation['activate'] = 'no'
                        self.logger(b'Automation temporarily off: No data to work with!')
                    else:
                        self.selected_index += 1
                        if self.selected_index >= len(self.servers_data[0]):
                            # current server list has run out, trigger the refresh on the next loop
                            self.servers_data = (None, None)
                            self.selected_index = -1
                        else:
                            self.vpn_connect(self.selected_index)

                if self.my_config.automation["fetch_interval"] >= "0.5":
                    if time.time() >= self.next_refresh_time:
                        self.logger(b'___ Automation entry point ___')
                        self.fetcher.fetch_data()
                        self.next_refresh_time = time.time() + float(self.my_config.automation["fetch_interval"]) * 3600

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
                   "vpn:{}"

        with open("logs/manager.log", "w+") as status:
            if self.exit:
                stat = template.format(0,'','','','')
            else:
                stat = template.format(1,os.getpid(), self.host, self.port, self.connected_vpn)

            status.write(stat)

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
    my_vpn_manager.loop()
