#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"

"""Different types of User Interface is defined here"""

import re
import time
import socket
import signal
import os, sys
from base import ctext, FavoriteSevers, Setting


def tell_server(address: tuple, cmd: str, get_response=False):
    #the caller must handle socket error, not here
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(address)
        sock.sendall(bytes(cmd + "\n", "utf-8"))
        if get_response:
            received = str(sock.recv(1024), "utf-8")
            return received


class Worker(object):
    """Used as a wrapper for func to be passed in process_log"""

    def __init__(self, func=None):
        self.func = func
        self.result = None

    def __call__(self, *args, **kwargs):
        if self.func:
            self.result = self.func(*args, **kwargs)
        return None


class UI(object):
    def __init__(self, my_config: Setting):
        # Open the latest log
        self.log = None
        self.log_open()
        self.seek_pos = 0

        self.type = 'UI base class'

        self.config = my_config
        self.network = ''
        self.filters = ''
        self.mirrors = ''
        self.mode = ''
        self.reload_config()

        self.time_stamp = ""
        self.sorted_vpn = []

        self.connected_servers = []
        self.isConnect = False

        # talk to the vpn_manager
        self.pid = 0
        self.host = 'localhost'
        self.port = 0
        self.connection = ''

    def reload_config(self):
        self.network = self.config.network
        self.filters = self.config.filter
        self.mirrors = self.config.mirrors
        self.mode = self.config.network['mode']

    def check_server(self, what='all'):
        """check if the vpn_manager is running and which port it is listening to"""
        if not os.path.exists("logs/manager.log"):
            return False

        with open("logs/manager.log") as manager:
            if manager.readline().strip() == '0':
                return False
            if what in ['all', 'basic']:
                self.pid = int(manager.readline().strip().split(":")[1])
                self.host = manager.readline().strip().split(":")[1]
                self.port = int(manager.readline().strip().split(":")[1])

                self.connection = manager.readline().strip().split(":", 1)[1]
                self.isConnect = True if self.connection else False

            if what in ['all', 'past']:
                self.connected_servers = [x.strip() for x in manager.readlines()]

            if what in ['all', 'seek']:

                self.seek_pos = int(self.send_cmd('ftell', True)[1])

            return True

    def send_cmd(self, cmd: str, need_return: bool = False):
        self.time_stamp = time.strftime("%H:%M:%S")

        while True:
            try:
                response = tell_server((self.host, self.port), cmd, need_return)
                return True, response

            except Exception:
                if not self.check_server('basic'):
                    print('Vpn Manager is offline!\n')
                    return False, None

    def input_handler(self):
        """should be overwritten in subclass"""
        pass

    def signal_handler(self, signum, frame):
        """should be overwritten in subclass"""
        pass

    def log_open(self):
        """ Open the latest log"""
        all_logs = re.findall(r"vpn_\d{8}.log", ''.join(os.listdir("logs")))
        last_log = sorted(all_logs)[-1]

        output = "logs/{}".format(last_log)
        if self.log and output != self.log.name:
            self.log.close()
            self.seek_pos = 0

        self.log = open(output, "r")

    def iter_log_line(self, seek_pos=None):
        """iter through each line of log until no line to be read"""

        if self.log.name[-12:-4] != time.strftime("%Y%m%d"):
            self.log_open()

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
        The func must accept 1 argument, that is the current line of log.
        At least 1 keyword must certainly happen and its func return None to
          break the loop
        If you want to get the return value of func, use class Worker.
        """

        is_found = False
        lines = self.iter_log_line()
        while True:
            try:
                line = next(lines)

                if not is_found:
                    if line[0:8] < self.time_stamp or line[0:8].count(':') != 2:
                        continue
                    else:
                        is_found = True

                print(line, end='')
                for keyword in key_func:
                    if keyword in line:
                        res = key_func[keyword](line.strip())
                        if res is not None:
                            continue
                        else:
                            return

            except StopIteration:
                time.sleep(0.5)
                lines = self.iter_log_line()


class CommandLineInterface(UI):
    def __init__(self, my_config: Setting):
        # Open the latest log
        super().__init__(my_config)

        self.type = 'TUI'
        self.sorted_vpn = []
        self.page = 1
        self.lpp = 15  # lines per page

        # check the manager server if it is running for 5 seconds timeout
        t0 = time.time()
        while time.time() - t0 < 5:
            res = self.check_server()
            if not res:
                time.sleep(1)
                print('.', end='')
            else:
                break
        else:
            print("VPN manager is not running!")
            sys.exit(1)

        self.possible_cmd = {"quit": ['q', 'exit', 'quit'],
                             "refresh": ['r', 'refresh'],
                             "config": ['c', 'config'],
                             "next page": ['.', '>'],
                             "prev page": [',', '<'],
                             "next vpn": ['n', 'next'],
                             "prev vpn": ['p', 'prev'],
                             "log": ['log'],
                             "status": ['status'],
                             "stop": ['stop'],
                             "auto on": ['auto on', 'aon'],
                             "auto off": ['auto off', 'aoff'],
                             "list": ['list', 'ls'],
                             "mode main": ['mode main'],
                             "mode favorite": ['mode fav', 'mode favorite'],
                             "add favorite": ['save', 'add fav', 'add favorite'],
                             "del favorite": ['remove', 'del', 'delete'],
                             "add local": ["add local"],
                             "fav alive": ['alive', 'check', 'check alive'], }

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
        favorites = FavoriteSevers()
        fav_ips = favorites.ip
        self.check_server('past')
        self.reload_config()

        if self.mode == 'main':
            if not os.path.exists("data.txt"):
                print("Data is not present! Told the manager to refresh ...")
                stat, _ = self.send_cmd('refresh')
                if stat:
                    self.process_log({'[fetcher] Done': lambda x: None})
                else:
                    return

            with open("data.txt", "r") as f:
                basic_config = f.readline().rstrip('\n')
                print(basic_config)

                labels = f.readline().rstrip()
                print(ctext(labels, 'gB'))

                self.sorted_vpn[:] = []
                for line in f:
                    self.sorted_vpn.append(line.rstrip('\n'))

            for line in self.sorted_vpn[self.lpp * (self.page - 1): self.lpp * self.page]:
                ip = line.split()[-2]
                inFav = 'Fav'.rjust(4) if ip in fav_ips else ''
                line += inFav

                if self.connected_servers and ip == self.connected_servers[-1]:
                    line = ctext(line, 'y')
                elif self.connected_servers and ip in self.connected_servers:
                    line = ctext(line, 'r')

                print(line)

        else:  # mode favorite
            self.sorted_vpn[:] = str(favorites).split('\n')
            data = str(favorites).split('\n')
            labels = data[0]
            print(ctext(labels, 'gB'))

            for ind, line in enumerate(data[1:]):
                ip = fav_ips[ind]

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
            stat, _ = self.send_cmd('refresh')
            if stat:
                self.page = 1
                self.process_log({'[fetcher] Done': lambda x: None})
                self.display()

        def config(arg):
            self.config.get_input()
            refresh(arg)

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
                template = "Manager's PID: {}\nHost: {}\nListening port: {}\nConnection: {}". \
                    format(self.pid, self.host, self.port, self.connection)
                print(template)

        def switch_mode(arg):
            _, mode = arg.split()
            self.mode = 'main' if mode == 'main' else 'favorite'
            to_manager(arg)
            time.sleep(0.5)
            self.display()

        def fav_alive(arg):
            my_worker = Worker(lambda x: [int(y) for y in x.split(' = ')[1].split(' ')])
            to_manager('check alive')
            self.process_log({'fav alive': my_worker})

        def del_fav(arg):
            agv = arg.split()
            to_manager(f"remove {' '.join(agv[1:])}")
            time.sleep(1)
            self.display()

        def add_local(arg):
            fs = FavoriteSevers()
            fs.add_local()
            self.display()

        def to_manager(arg):
            self.send_cmd(arg)

        func = {"quit": quit,
                "refresh": refresh,
                "config": config,
                "next page": next_page,
                "prev page": previous_page,
                "next vpn": to_manager,
                "prev vpn": to_manager,
                "log": show_log,
                "status": status,
                "stop": to_manager,
                "auto on": to_manager,
                "auto off": to_manager,
                "list": self.display,
                "mode main": switch_mode,
                "mode favorite": switch_mode,
                "add favorite": to_manager,
                "del favorite": del_fav,
                "add local": add_local,
                "fav alive": fav_alive,
                }
        # ↑_finish defining mini method___↑↑↑

        # reload the config
        self.config.load()

        server_sum = len(self.sorted_vpn) if self.mode == 'main' else len(FavoriteSevers())
        user_input = input(ctext('Vpn command: ', 'gB')).strip().lower()
        if not user_input:
            return

        # user inputs a number
        if user_input[0].isdigit():
            if re.findall(r'^\d+$', user_input) and int(user_input) < server_sum:
                chosen = int(user_input)

                stat, _ = self.send_cmd('connect %s' % chosen)
                if stat:
                    self.isConnect = True
                    self.process_log({'[vpn manager] done': lambda x: None})
            else:
                print('No such server!\n')

        else:
            for key in self.possible_cmd:
                ui = re.findall(r'[a-zA-Z .,<>]+', user_input)[0].strip()
                if ui in self.possible_cmd[key]:
                    func[key](user_input)
                    break

            else:
                print('Invalid command!')
                print('  q(uit) to quit\n  r(efresh) to refresh table\n'
                      '  c(onfig) to change setting\n  number in range 0~%s to choose vpn\n' % (server_sum - 1))

    def signal_handler(self, signum, frame):
        if not self.isConnect:
            print(ctext('Goodbye'.center(40), 'gB'))
            sys.exit()
        else:
            self.SIGINT = True
            print(' Goodbye  ')
            sys.exit(0)

    def loop(self):
        if self.config.automation["activate"] == 'yes':
            print("vpn is connecting")
            print(self.connection)

        while True:
            self.input_handler()


if __name__ == '__main__':
    if len(sys.argv[1:]) > 1:
        addr = sys.argv[1]
        port = sys.argv[2]
        cmd = sys.argv[3]
        print(tell_server((addr, int(port)), cmd))
        sys.exit(0)

    # todo: enforce the tcp communication always wait for response

    my_conf = Setting()
    my_conf.check()
    tui = CommandLineInterface(my_conf)
    signal.signal(signal.SIGINT, tui.signal_handler)
    tui.loop()
