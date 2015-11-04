#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "duc_tin"
__copyright__ = "Copyright 2015+, duc_tin"
__license__ = "GPLv2"
__version__ = "1.1"
__maintainer__ = "duc_tin"
__email__ = "nguyenbaduc.tin@gmail.com"

import urwid

# -----------------------------------------------here we go-------------------------------------------------------------


class MyText(urwid.Text):
    signals = ['click']

    def __init__(self, markup, wrap='clip'):
        super(MyText, self).__init__(markup, wrap=wrap)
        self._selectable = True

    def keypress(self, size, key):
        if key == 'f10':
            self._emit('click')
        else:
            return key


class MyButton(urwid.Button):
    def __init__(self, caption, callback):
        super(MyButton, self).__init__(caption)
        urwid.connect_signal(self, 'click', callback)
        self._w = urwid.AttrMap(urwid.SelectableIcon([u' \N{BULLET} ', caption], 1), None, 'popbgs')

    def update_label(self, newcap):
        caption = newcap
        self._w = urwid.AttrMap(urwid.SelectableIcon([u' \N{BULLET} ', caption], 1), None, 'popbgs')


class MyColumn(urwid.Columns):
    def __init__(self, widget_list, dividechars=1, focus_column=None, min_width=1, box_columns=None):
        super(MyColumn, self).__init__(widget_list, dividechars, focus_column, min_width, box_columns)

        self.receiver = {}
        for col, widget in enumerate(widget_list):
            if hasattr(widget, 'trigger') and widget.trigger:
                self.receiver[widget.trigger] = col

    def keypress(self, size, key):
        if key == 'up':
            return key
        if key in self.receiver:
            receiver = self.receiver[key]
            self.set_focus_column(receiver)

        return super(MyColumn, self).keypress(size, key)


class MyPile(urwid.Pile):
    def __init__(self, widget_list, focus_item=None):
        super(MyPile, self).__init__(widget_list, focus_item)

    def keypress(self, size, key):
        if key == 'up':
            return key

        if len(key) == 2 and 'f' in key:
            self.focus_position = 0
        else:
            self.focus_position = 1

        return super(MyPile, self).keypress(size, key)


class PopUpSortBy(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button """
    signals = ['close']

    def __init__(self, key=None, value=''):
        self.chosen = 'ping' if value == '' else value
        self.trigger = key

        ping = MyButton("ping", self.item_callback)
        speed = MyButton("speed", self.item_callback)
        uptime = MyButton("up time", self.item_callback)
        score = MyButton("score", self.item_callback)

        default = {'ping': 0, 'speed': 1, 'up time': 2, 'score': 3}

        self.pile = urwid.Pile([ping, speed, uptime, score], focus_item=default[self.chosen])
        fill = urwid.LineBox(urwid.Filler(self.pile))
        self.__super.__init__(urwid.AttrWrap(fill, 'popbg'))

    def item_callback(self, Button, data=None):
        self.chosen = self.pile.focus.label
        self._emit("close")

    def keypress(self, size, key):
        if key in [self.trigger, 'esc']:
            self._emit("close")
            return self.trigger
        else:
            self.pile.keypress(size, key)


class PopUpCountry(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button """
    signals = ['close']

    def __init__(self, key=None, value=''):
        self.trigger = key
        info = urwid.Text("'ESC' to clear, leave blank for all country", 'center')
        self.filter = urwid.Edit('Name: ', edit_text=value, wrap='clip')
        filter_ = urwid.AttrMap(self.filter, None, 'popbgs')

        self.pile = urwid.Pile([info, filter_])
        fill = urwid.LineBox(urwid.Filler(self.pile))
        self.__super.__init__(urwid.AttrWrap(fill, 'popbg'))

        self.chosen = self.filter.get_edit_text()

    def keypress(self, size, key):
        if key in [self.trigger, 'esc']:
            self.filter.set_edit_text(self.chosen)
            self._emit("close")
        elif key == 'esc':
            self.filter.set_edit_text('')

        elif key == 'enter':
            self.chosen = self.filter.get_edit_text()
            self.chosen = 'all' if not self.chosen else self.chosen
            self.filter.keypress((size[0],), key)
            self._emit("close")
        else:
            self.filter.keypress((size[0],), key)


class PopUpProxy(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button """
    signals = ['close']

    def __init__(self, key=None, value=('', '')):
        self.trigger = key
        self.yn = value[0]
        self.yn_but = MyButton('Use proxy: ' + self.yn, self.on_change)
        self.input_addr = urwid.Edit(u' \N{BULLET} Address  : ', edit_text=value[1], wrap='clip')
        self.input_port = urwid.IntEdit(u' \N{BULLET} Port     : ', default=value[2])
        self.input_port.set_wrap_mode('clip')
        exit_but = urwid.Padding(urwid.Button('OKay'.center(8), self.item_callback), 'center', 12)

        widgets = [self.yn_but] \
                  + [urwid.AttrMap(wid, None, 'popbgs') for wid in (self.input_addr, self.input_port, exit_but)]

        self.pile = urwid.Pile(widgets)
        fill = urwid.LineBox(urwid.Filler(self.pile))
        self.__super.__init__(urwid.AttrWrap(fill, 'popbg'))

        self.chosen = value

    def on_change(self, Button, data=None):
        self.yn = 'no' if 'y' in self.yn else 'yes'
        self.yn_but.update_label('Use proxy: ' + self.yn)

    def item_callback(self, Button, data=None):
        port = self.input_port.edit_text
        addr = self.input_addr.edit_text.replace('http://', '')
        if self.yn == 'yes':
            if 'Invalid' in addr + port:
                return
            if not addr or not port:
                self.input_addr.set_edit_text('Invalid Address!')
            if not 0 <= int(port) <= 65535:
                self.input_port.set_edit_text('Invalid number!')
            else:
                self.chosen = self.yn, addr, port
                self._emit("close")
        else:
            self.chosen = self.yn, addr, port

            self._emit("close")

    def keypress(self, size, key):
        position = self.pile.focus_position
        if key == self.trigger:
            self.input_addr.set_edit_text(self.chosen[1])
            self.input_port.set_edit_text(self.chosen[2])
            self._emit("close")
        elif key == 'esc':
            if position == 1 and self.input_addr.edit_text:
                self.input_addr.set_edit_text('')
            elif position == 2 and self.input_port.edit_text:
                self.input_port.set_edit_text('')
            else:
                self.input_addr.set_edit_text(self.chosen[1])
                self.input_port.set_edit_text(self.chosen[2])
                self._emit("close")
        elif key == 'enter' and 0 < position < len(self.pile.widget_list)-1:
            self.pile.focus_position += 1
        else:
            self.pile.keypress((size[0],), key)


class PopUpDNS(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button """
    signals = ['close']

    def __init__(self, key=None, value=('', '')):
        self.trigger = key
        self.yn = value[0]
        self.yn_but = MyButton('Fix it: ' + self.yn, self.on_change)
        self.input_dns = urwid.Edit(u' \N{BULLET} DNS : ', edit_text=value[1], wrap='clip')
        exit_but = urwid.Padding(urwid.Button('OKay'.center(8), self.item_callback), 'center', 12)

        widgets = [self.yn_but] + [urwid.AttrMap(wid, None, 'popbgs') for wid in (self.input_dns, exit_but)]

        self.pile = urwid.Pile(widgets)
        fill = urwid.LineBox(urwid.Filler(self.pile))
        self.__super.__init__(urwid.AttrWrap(fill, 'popbg'))

        self.chosen = value

    def on_change(self, Button, data=None):
        self.yn = 'no' if 'y' in self.yn else 'yes'
        self.yn_but.update_label('Fix it: ' + self.yn)

    def item_callback(self, Button, data=None):
        self.chosen = self.yn, self.input_dns.edit_text
        self._emit("close")

    def keypress(self, size, key):
        position = self.pile.focus_position
        if key in [self.trigger, 'esc']:
            self.input_dns.set_edit_text(self.chosen[1])
            self._emit("close")
        elif key == 'enter' and 0 < position < len(self.pile.widget_list)-1:
            self.pile.focus_position += 1
        else:
            self.pile.keypress((size[0],), key)


class AddPopUp(urwid.PopUpLauncher):
    signals = ['done']

    def __init__(self, target_widget, popup, value, trigger, size):
        self.__super.__init__(target_widget)
        self.popup = popup(key=trigger, value=value)
        self.trigger = trigger
        self.size = size
        self.result = value

    def create_pop_up(self):
        # this method must be exist due to its blank content in original class
        urwid.connect_signal(self.popup, 'close', self.close_pop)
        return self.popup

    def get_pop_up_parameters(self):
        l, t, w, h = self.size
        # 3, 1, 12, 6
        return {'left': l, 'top': t, 'overlay_width': w, 'overlay_height': h}

    def keypress(self, size, key):
        if key == self.trigger:
            self.open_pop_up()
        else:
            return key

    def close_pop(self, button):
        self.result = button.chosen
        self.close_pop_up()
        self._emit('done', self.trigger)
