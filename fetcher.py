#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"

import socket
import re
import requests
import time
from subprocess import Popen, PIPE
from threading import Thread
from queue import Queue
from base import Server, Setting
from functools import partial


class Fetcher:
    def __init__(self, logger):
        self.config = Setting()
        self.logger = partial(logger, source=b'[fetcher]')
        
        # data for using across the class method
        self.filters = self.network = self.mirrors = None

        # write out formatted data
        labels = ['Idx', 'Geo', 'Ping', 'Speed', 'UpTime', 'Log', 'Score', 'proto', 'Ip', 'Port']
        self.spaces = [5, 4, 5, 8, 12, 4, 8, 6, 16, 6]
        self.labels = [label.center(self.spaces[ind]) for ind, label in enumerate(labels)]

    def _get_data(self):
        use_proxy = self.network['use_proxy']
        self.mirrors.insert(0, 'http://www.vpngate.net')

        if use_proxy == 'yes':
            proxy = self.network['proxy']
            port = self.network['proxy']
            ip = self.network['ip']

            ping_name = ['ping', '-w 2', '-c 2', proxy]
            ping_ip = ['ping', '-w 2', '-c 2', ip]
            res1, err1 = Popen(ping_name, stdout=PIPE, stderr=PIPE).communicate()
            res2, err2 = Popen(ping_ip, stdout=PIPE, stderr=PIPE).communicate()

            if err1 and not err2:
                self.logger(b"Warning: Cannot resolve proxy's hostname")
                proxy = ip
            if err1 and err2:
                self.logger(b'Ping proxy got error: '+err1)
                self.logger(b'Check your proxy setting')
            if not err1 and '100% packet loss' in res1:
                self.logger(b'Warning: Proxy not response to ping')
                self.logger(b"Either proxy's security not allow it to response to ping packet or proxy itself is dead")

            proxies = {'http' : 'http://' + proxy + ':' + port,
                       'https': 'http://' + proxy + ':' + port}

        else:
            proxies = {}

        i = 0
        while i < len(self.mirrors):
            try:
                self.logger(bytes('using gate: ' + self.mirrors[i], "ascii"))
                gate = self.mirrors[i] + '/api/iphone/'
                vpn_data = requests.get(gate, proxies=proxies, timeout=3).text.replace('\r', '')

                if 'vpn_servers' not in vpn_data:
                    raise requests.exceptions.RequestException

                servers = [line.split(',') for line in vpn_data.split('\n')]
                servers = {s[0]: Server(s) for s in servers[2:] if len(s) > 1}
                return servers
            except requests.exceptions.RequestException as e:
                self.logger(bytes(str(e), 'ascii'))
                self.logger(bytes('Connection to gate %s failed' % self.mirrors[i], 'ascii'))
                i += 1
        else:
            self.logger(b'Failed to get VPN servers data\nCheck your network setting and proxy')

    def _is_alive(self, servers, vpndict, queue):
        use_proxy = self.network['use_proxy']
        timeout = int(self.network['timeout'])
        target = [(vpndict[name].ip, vpndict[name].port) for name in servers]

        if use_proxy == 'yes':
            ip = self.network['proxy']
            port = self.network['port']
            test_interval = self.network['test_interval']

            for i in range(len(target)):
                s = socket.socket()
                s.settimeout(timeout)
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
                s.settimeout(timeout)
                ip, port = target[i]
                try:
                    s.connect((ip, int(port)))
                    s.shutdown(socket.SHUT_RD)
                except socket.timeout:
                    queue.put(servers[i])
                except Exception as e:
                    # print e
                    queue.put(servers[i])
                finally:
                    s.close()
                    # time.sleep(test_interval)      # no need since we make connection to different servers

    def _probe(self, vpndict: dict):
        """ Filter out fetched dead Vpn Servers """

        my_queue = Queue()
        chunk_len = 10  # reduce chunk_len will increase number of thread
        my_chunk = [list(vpndict.keys())[i:i + chunk_len] for i in range(0, len(vpndict), chunk_len)]
        my_thread = []

        for chunk in my_chunk:
            t = Thread(target=self._is_alive, args=(chunk, vpndict, my_queue))
            t.start()
            my_thread.append(t)

        for t in my_thread:
            t.join()

        count = 0
        total = len(vpndict)
        while not my_queue.empty():
            count += 1
            dead_server = my_queue.get()
            del vpndict[dead_server]

        self.logger(bytes('Deleted %d dead servers out of %d' % (count, total), 'ascii'))

    def fetch_data(self):
        # get the newest config
        self.config.load()
        self.filters = self.config.filter
        self.network = self.config.network
        self.mirrors = self.config.mirrors
        self.mirrors = self.mirrors['url'].split(', ')

        # fetch data from vpngate.net
        self.logger(b"fetching data")
        vpn_dict = self._get_data()

        s_country = self.filters['country']
        s_port = self.filters['port']
        s_score = self.filters['score']
        s_proto = self.filters['proto']
        sort_by = self.filters['sort_by']

        if vpn_dict:
            if s_country != 'all':
                vpn_dict = dict([vpn for vpn in vpn_dict.items()
                                if re.search(r'\b%s\b' % s_country, vpn[1].country_long.lower() + ' '
                                             + vpn[1].country_short.lower())])
            if s_port != 'all':
                if s_port[0] == '>':
                    vpn_dict = dict([vpn for vpn in vpn_dict.items() if int(vpn[1].port) > int(s_port[1:])])
                elif s_port[0] == '<':
                    vpn_dict = dict([vpn for vpn in vpn_dict.items() if int(vpn[1].port) < int(s_port[1:])])
                else:
                    vpn_dict = dict([vpn for vpn in vpn_dict.items() if vpn[1].port in s_port])

            if s_proto != 'all':
                vpn_dict = dict([vpn for vpn in vpn_dict.items() if vpn[1].proto == s_proto])

            if s_score != 'all':
                vpn_dict = dict([vpn for vpn in vpn_dict.items() if int(vpn[1].score) > int(s_score)])

        if not vpn_dict:
            self.logger(b"No thing to do !")
            sort = None
        else:
            self.logger(b"Filtering out dead VPN...")
            self._probe(vpn_dict)

            if sort_by == 'speed':
                sort = sorted(vpn_dict.keys(), key=lambda x: vpn_dict[x].speed, reverse=True)
            elif sort_by == 'ping':
                sort = sorted(vpn_dict.keys(), key=lambda x: vpn_dict[x].ping)
            elif sort_by == 'score':
                sort = sorted(vpn_dict.keys(), key=lambda x: vpn_dict[x].score, reverse=True)
            elif sort_by == 'up time':
                sort = sorted(vpn_dict.keys(), key=lambda x: int(vpn_dict[x].uptime))
            else:
                self.logger(bytes('ValueError: sort_by must be in "speed|ping|score|up time". Got "%s" instead.' % sort_by), 'ascii')
                self.logger(b'Change your setting by "$ ./vpnproxy config"')
                return

        # write to file
        self._write(sort, vpn_dict)
        self.logger(b'Done')
        return sort, vpn_dict

    def _write(self, sorted_vpn, vpndict):
        """UI shall read the written file for display"""
        network = self.network
        filters = self.filters

        with open("data.txt", "w+") as f:
            f.write(' Use proxy: %s | Country: %s | Min score: %s | Proto: %s | Portal:%s\n' %
                    (network['use_proxy'], filters['country'], filters['score'], filters['proto'], filters['port']))

            if not sorted_vpn:
                f.write('No server found for current condition')

            else:
                f.write(''.join(self.labels)+'\n')
                for index, key in enumerate(sorted_vpn):
                    text = '%2d:'.center(6) % index + str(vpndict[key])
                    f.write(text+'\n')
