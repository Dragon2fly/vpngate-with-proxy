#!/usr/bin/env python 
# -*- coding: utf-8 -*-
import select

__author__ = 'duc_tin'

from gi.repository import Gtk, GLib
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify
from Queue import Queue, Empty
import signal, os
import random
import socket
import time


class VPNIndicator:
    def __init__(self):
        self.APPINDICATOR_ID = 'myappindicator'
        self.icon1 = os.path.abspath('drawing.svg')
        self.icon2 = os.path.abspath('drawing_fail.svg')
        self.icon3 = os.path.abspath('connecting.gif')

        self.state = 2
        self.indicator = appindicator.Indicator.new(self.APPINDICATOR_ID, self.icon2,
                                                    appindicator.IndicatorCategory.APPLICATION_STATUS)

        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

        # Add menu to indicator
        self.indicator.set_menu(self.build_menu())

        self.notifier = notify.Notification.new('', '', None)
        self.notifier.set_timeout(2)

        notify.init(self.APPINDICATOR_ID)

    def run(self, callback, *args):
        GLib.timeout_add(3000, callback, *args)
        Gtk.main()

    def reload(self, data_in):
        if data_in:
            print data_in
            if 'successfully' in data_in:
                self.indicator.set_icon(self.icon1)
                self.status('', ['successfully'])
            elif 'terminate' in data_in:
                self.indicator.set_icon(self.icon2)
                self.status('', ['terminate'])
        return True

    def build_menu(self):
        menu = Gtk.Menu()

        item_joke = Gtk.MenuItem('VPN Status')
        item_joke.connect('activate', self.status)
        menu.append(item_joke)

        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def quit(self, source):
        notify.uninit()
        Gtk.main_quit()

    def status(self, _, messages=[0]):
        """

        :type messages: list
        """

        self.notifier.close()

        if 'successfully' in messages[0]:
            summary = 'VPN tunnel established'
            self.indicator.set_icon(self.icon1)
            body = '''
            %s
            %s
            %s
            ''' % ('Japan', '126.220.10.238', '202.28 Mbps')
        else:
            self.indicator.set_icon(self.icon2)
            summary = 'VPN tunnel has broken'
            body = ' not thing to show'

        self.notifier.update(summary, body, icon=None)
        self.notifier.show()


class InfoServer:
    def __init__(self, port):
        self.host = 'localhost'
        self.data_payload = 2048     # buffer
        self.backlog = 1
        self.client = None

        self.port = port
        self.sock = socket.socket()
        # self.sock.setblocking(0)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_address = self.host, self.port
        self.last_msg = ''

    def run(self, q_in, q_out):
        # print 'starting server at %s:%s' % server_address
        self.sock.bind(self.server_address)
        self.sock.listen(self.backlog)

        # wait forever for an incoming connection from indicator
        self.client, address = self.sock.accept()

        while True:
            try:
                ready = select.select([self.client], [], [], 1)
                if ready[0]:
                    data = self.client.recv(self.data_payload)
                    if 'close' in data:
                        self.client.close()
                        self.client, address = self.sock.accept()
                        self.client.sendall(self.last_msg)

                info = q_in.get_nowait()
                self.client.sendall(info)
                self.last_msg = info
            except Empty:
                time.sleep(1)
            except IOError, e:
                print str(e)

    def stop(self):
        self.client.close()


class InfoClient:
    def __init__(self, port):
        self.port = port
        self.host = 'localhost'
        self.data_payload = 2048     # buffer
        self.sock = socket.socket()
        self.server_address = self.host, port

    def connect(self):
        # print 'connect to %s:%s' % server_address
        attempt = 3
        while attempt:
            try:
                self.sock.connect(self.server_address)
                break
            except socket.error, e:
                time.sleep(10)
                attempt -= 1
        else:
            handler('', '')

    def get_data(self):
        self.check_alive()
        data = ''
        try:
            ready = select.select([self.sock], [], [], 1)
            if ready[0]:
                data = self.sock.recv(self.data_payload)
        except socket.errno, e:
            print 'Socket error: ' + str(e)
        except Exception, e:
            print 'program error: '+ str(e)

        return data

    def check_alive(self):
        try:
            self.sock.send('hello')
        except socket.error, e:
            if 'Broken pipe' in e:
                self.connect()
            else:
                print str(e)


def callback(client, indica):
        """
        :type client: InfoClient
        :type indica: VPNIndicator
        """
        data = client.get_data()
        indica.reload(data)
        return True


def handler(signal_num, frame):
    print 'interrupt now'
    try:
        me.sock.send('close')
        me.sock.close()
    except socket.error:
        pass
    indicator.quit('')

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handler)
    me = InfoClient(8088)
    me.connect()
    print 'connected'
    indicator = VPNIndicator()
    indicator.run(callback, me, indicator)

