#!/usr/bin/env python 
# -*- coding: utf-8 -*-
import select

__author__ = 'duc_tin'

from Queue import Queue, Empty
import signal, os
import socket
import time

try:
    from gi.repository import Gtk, GLib
    from gi.repository import AppIndicator3 as appindicator
    from gi.repository import Notify as notify
except ImportError:
    print 'Lack of Gtk related modules!'
    print 'VPN indicator will not run!'


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
        self.first_connect = True

    def connect(self):
        # print 'connect to %s:%s' % server_address
        attempt = 1
        while attempt:
            try:
                self.sock = socket.create_connection(self.server_address)
                print 'connected'
                return True
                break
            except socket.error, e:
                print 'Socket error: ' + str(e)
                time.sleep(5)
                attempt -= 1
        else:
            return False

    def get_data(self):
        if not self.check_alive():
            return 'Offline'
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
        if self.first_connect:
            self.first_connect = False
            return self.connect()

        try:
            self.sock.send('hello')
            return True
        except socket.error, e:
            if 'Broken pipe' in e or 'Bad file descriptor' in e:
                print 'server die'
                self.sock.close()
                return self.connect()
            else:
                print 'Socket error: ' + str(e)


class VPNIndicator:
    def __init__(self, tcp_client):
        signal.signal(signal.SIGINT, self.handler)
        signal.signal(signal.SIGTERM, self.handler)
        self.tcpClient = tcp_client
        self.APPINDICATOR_ID = 'myappindicator'
        self.icon1 = os.path.abspath('drawing.svg')
        self.icon2 = os.path.abspath('drawing_fail.svg')
        self.icon3 = os.path.abspath('connecting.gif')

        self.last_recv = ''
        self.trial = 4
        self.indicator = appindicator.Indicator.new(self.APPINDICATOR_ID, self.icon2,
                                                    appindicator.IndicatorCategory.APPLICATION_STATUS)

        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

        # Add menu to indicator
        self.indicator.set_menu(self.build_menu())

        self.notifier = notify.Notification.new('', '', None)
        self.notifier.set_timeout(2)

        notify.init(self.APPINDICATOR_ID)
        self.run()

    def run(self, *args):
        GLib.timeout_add(2000, self.callback, *args)
        Gtk.main()

    def reload(self, data_in):
        if data_in:
            self.last_recv = data_in.split(';')
            if 'successfully' in data_in:
                self.indicator.set_icon(self.icon1)
                self.status('', self.last_recv)
            elif 'terminate' in data_in:
                self.indicator.set_icon(self.icon2)
                self.status('', ['terminate'])
            elif 'Offline' in data_in:
                self.indicator.set_icon(self.icon2)
                self.status('', ["Offline"])
                self.trial -= 1
            else:
                self.trial = 3
        return True

    def build_menu(self):
        menu = Gtk.Menu()

        item_joke = Gtk.MenuItem('VPN Status')
        item_joke.connect('activate', self.status, self.last_recv)
        menu.append(item_joke)

        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', self.handler, '')
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
        if _:
            messages = self.last_recv
        self.notifier.close()

        if 'successfully' in messages[0]:
            summary = 'VPN tunnel established'
            body = '''
            %s \t             %s
            Ping: \t\t\t%s
            Speed: \t\t\t%s MB/s
            Up time:\t\t%s
            Season: \t\t%s
            Log: \t\t\t%s
            Score: \t\t\t%s
            Protocol: \t\t%s
            ''' % tuple(messages[1:])
        elif 'terminate' in messages[0]:
            summary = 'VPN tunnel has broken'
            body = 'Please choose a different server and try again'
        elif 'Offline' in messages[0]:
            summary = 'VPN program is offline'
            body = 'Stop indicator after %s time fail to reconnect' % self.trial

        self.notifier.update(summary, body, icon=None)
        self.notifier.show()

    def handler(self, signal_num, frame):
        print 'interrupt now'
        self.quit('')
        try:
            self.tcpClient.sock.send('close')
            self.tcpClient.sock.close()
        except socket.error:
            pass

    def callback(self):
        if self.trial:
            data = self.tcpClient.get_data()
            self.reload(data)
            return True
        else:
            self.handler('', '')

if __name__ == '__main__':
    me = InfoClient(8088)
    indicator = VPNIndicator(me)

