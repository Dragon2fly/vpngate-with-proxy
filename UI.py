#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"

"""Different types of User Interface is defined here"""

import re
import time
import socket
import signal
import os, sys
from base import ctext


def tell_server(address: tuple, cmd: str, need_return: bool = False):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # Connect to server and send data
        sock.connect(address)
        sock.sendall(bytes(cmd + "\n", "utf-8"))

        # Receive data from the server then shut down
        if need_return:
            received = str(sock.recv(1024), "utf-8")
            return received


class UI(object):
    def __init__(self, my_config):
        # Open the latest log
        self.log = None
        self.log_open()
        self.seek_pos = 0

        self.type = 'UI base class'

        self.config = my_config
        self.network = my_config.network
        self.filters = my_config.filter
        self.mirrors = my_config.mirrors

        self.time_stamp = ""
        self.sorted_vpn = []

        self.connected_servers = []
        self.isConnect = False

        # talk to the vpn_manager
        self.host = 'localhost'
        self.port = 0
        self.pid = 0
        self.connection = ''

    def check_server(self):
        """check if the vpn_manager is running and which port it is listening to"""
        if not os.path.exists("logs/manager.log"):
            return False

        with open("logs/manager.log") as manager:
            if manager.readline().strip() == '0':
                return False

            self.pid = int(manager.readline().strip().split(":")[1])
            self.host = manager.readline().strip().split(":")[1]
            self.port = int(manager.readline().strip().split(":")[1])
            self.connection = manager.readline().strip().split(":")[1]
            self.isConnect = True if self.connection else False

            self.seek_pos = int(self.send_cmd('ftell', True))

            return  True

    def send_cmd(self, cmd: str, need_return: bool = False):
        self.time_stamp = time.strftime("%H:%M:%S")
        response = tell_server((self.host, self.port), cmd, need_return)
        if need_return:
            return response

    def input_handler(self):
        """should be overwritten in subclass"""
        pass

    def signal_handler(self, signum, frame):
        """should be overwritten in subclass"""
        pass

    def log_open(self):
        """ Open the latest log"""
        if self.log:
            self.log.close()

        all_logs = re.findall(r"vpn_\d{8}.log", ''.join(os.listdir("logs")))
        last_log = sorted(all_logs)[-1]
        output = "logs/{}".format(last_log)
        self.log = open(output, "r")

    def iter_log_line(self, seek_pos=None):
        if not seek_pos:
            seek_pos = self.seek_pos

        self.log.seek(seek_pos)
        while True:
            line = self.log.readline()
            if not line:
                self.seek_pos = self.log.tell()
                return
            else:
                yield line

                if "next day" in line:
                    self.log_open()

    def process_log(self, key_func: dict):
        """read the log line by line, 
        scan for keyword and execute the func that is associated with it
        At least 1 keyword will certainly happen and it's func is None to
          break the loop
        """

        lines = self.iter_log_line()
        while True:
            try:
                line = next(lines)
                print(line, end='')
                for keyword in key_func:
                    if keyword in line:
                        if key_func[keyword]:
                            key_func[keyword]()
                        else:
                            return

            except StopIteration:
                time.sleep(0.5)
                lines = self.iter_log_line()


class TerminalUserInterface(UI):
    def __init__(self, my_config):
        # Open the latest log
        super().__init__(my_config)

        self.type = 'TUI'
        self.sorted_vpn = []
        self.last_mtime = 0  # last modified time
        self.page = 1
        self.lpp = 15  # lines per page

        # check the manager server if it is running
        t0 = time.time()
        while time.time() - t0 < 5:
            res = self.check_server()
            if not res:
                time.sleep(1)
            else:
                break
        else:
            print("VPN manager is not running!")
            sys.exit(1)

        self.possible_cmd = {"quit": ['q', 'exit', 'quit'],
                             "refresh": ['r', 'refresh'],
                             "config": ['c', 'config'],
                             "next page": ['n', 'next','.', '>'],
                             "prev page": ['p', 'previous', ',','<'],
                             "log": ['log'],
                             "status": ['status'],
                             "stop": ['stop'],
                             "auto on": ['auto on', 'aon'],
                             "auto off": ['auto off', 'aoff'],
                             "list": ['list']}

    def set_page(self, direction):
        max_page = int(len(self.sorted_vpn) / self.lpp) + 1
        if direction in ["n", "next"]:
            self.page += 1
            if self.page > max_page:
                self.page = 1
        if direction in ["p", "previous"]:
            self.page -= 1
            if self.page < 1:
                self.page = max_page

    def display(self, arg=None):
        if not os.path.exists("data.txt"):
            print("Data is not present! Told the manager to refresh ...")
            self.send_cmd('refresh')
            self.process_log({'[fetcher] Done': None})

        with open("data.txt", "r") as f:
            basic_config = f.readline().rstrip()
            print(basic_config)

            labels = f.readline().rstrip()
            print(ctext(labels, 'gB'))

            # if file is new, re read it
            mtime = os.path.getmtime(f.name)
            if mtime != self.last_mtime:
                self.last_mtime = mtime
                self.sorted_vpn[:] = []
                for line in f:
                    self.sorted_vpn.append(line.rstrip())

        for line in self.sorted_vpn[self.lpp * (self.page - 1): self.lpp * self.page]:
            ip = line.split()[-1]
            if self.connected_servers and ip == self.connected_servers[-1]:
                line = ctext(line, 'y')
            elif self.connected_servers and ip in self.connected_servers:
                line = ctext(line, 'r')

            print(line)

    def input_handler(self):
        """process command from user"""

        # def mini methods___↓↓↓
        # running speed maybe slow down a bit but I don't care
        def quit(arg):
            print(ctext('Goodbye'.center(40), 'gB'))
            sys.exit(0)

        def refresh(arg):
            self.send_cmd('refresh')

        def config(arg):
            self.config.get_input()
            self.send_cmd('refresh')

        def next_page(arg):
            self.set_page("next")
            self.display(arg)

        def previous_page(arg):
            self.set_page("previous")
            self.display()

        def show_log(arg):
            for line in self.iter_log_line():
                print(line, end='')

        def status(arg):
            if not self.check_server():
                print("VPN manager is offline")
            else:
                template="Manager's PID: {}\nHost: {}\nListening port: {}\nConnection: {}".\
                    format(self.pid, self.host, self.port, self.connection)
                print(template)

        def to_manager(arg):
            self.send_cmd(arg)

        func = {"quit": quit,
                "refresh": refresh,
                "config": config,
                "next page": next_page,
                "prev page": previous_page,
                "log": show_log,
                "status": status,
                "stop": to_manager,
                "auto on": to_manager,
                "auto off": to_manager,
                "list": self.display}
        # ↑_finish defining mini method___↑↑↑

        server_sum = len(self.sorted_vpn)
        user_input = input(ctext('Vpn command: ', 'gB')).strip().lower()

        # user inputs a number
        if re.findall(r'^\d+$', user_input) and int(user_input) < server_sum:
            chosen = int(user_input)

            print(time.ctime().center(40))
            self.connected_servers.append(self.sorted_vpn[chosen].split()[-1])

            self.send_cmd('connect %s' % chosen)
            self.isConnect = True

        else:
            for key in self.possible_cmd:
                if user_input in self.possible_cmd[key]:
                    func[key](user_input)
                    break

            else:
                print('Invalid command!')
                print('  q(uit) to quit\n  r(efresh) to refresh table\n'
                      '  c(onfig) to change setting\n  number in range 0~%s to choose vpn\n' % (server_sum - 1))
                time.sleep(3)

    def signal_handler(self, signum, frame):
        if not self.isConnect:
            print(ctext('Goodbye'.center(40), 'gB'))
            sys.exit()
        else:
            self.SIGINT = True
            print('interrupt now')

    def loop(self):
        self.check_server()     # for port and its status
        if self.config.automation["activate"] == 'True':
            print("vpn is connecting")
            print(self.connection)

        while True:
            self.input_handler()


if __name__ == '__main__':
    if len(sys.argv[1:]) > 1:
        addr=sys.argv[1]
        port=sys.argv[2]
        cmd=sys.argv[3]
        print(tell_server((addr, int(port)), cmd))
        sys.exit(0)

    from base import Setting

    # todo : ask the status of vpn_manager to decide to refresh or not


    my_conf = Setting()
    my_conf.check()
    my_conf.load()
    tui = TerminalUserInterface(my_conf)
    signal.signal(signal.SIGINT, tui.signal_handler)
    tui.loop()
