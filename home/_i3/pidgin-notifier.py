#!/usr/bin/env python2
import re
import os
import subprocess
import shlex
import dbus, gobject
from dbus.mainloop.glib import DBusGMainLoop
import logging
from HTMLParser import HTMLParser
logging.basicConfig(level=logging.DEBUG)
from Xlib import X, display, Xutil
import ConfigParser
from datetime import datetime

from urllib2 import urlopen, Request
from urllib import urlencode

################################################################################
### Configure these to your liking:
################################################################################
MENTION_REGEX = re.compile('@ryan$|@ryan\W|EnigmaCurry|@all|@here', re.IGNORECASE)
MENTION_NOTIFY_CMD = "i3-nagbar -m \"{sender} mentioned you in {room} : {message}\" -t warning -b 'Focus IM' 'i3-msg workspace im; killall i3-nagbar'"
IM_NOTIFY_CMD = "i3-nagbar -m \"{sender} said to you: {message}\" -t warning -b 'Focus IM' 'i3-msg workspace im; killall i3-nagbar'"
NOTIFY_SPAM_INTERVAL = 300 # seconds of silence from a user before sending a new IM notification for them
IGNORE_CHANNEL = ['#bitcoin-otc']
################################################################################

def find_window(name, w):
    for win in w.query_tree().children:
        if win.get_wm_class() and win.get_wm_class()[1] == name:
            return win
        
        if len(win.query_tree().children) > 0:
            a = find_window(name, win)
            if a:
                return a

class Notifier(object):
    "Manage notifications"
    def __init__(self):
        self.config = self.__get_config()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self._nag_process = None
        self.bus.add_signal_receiver(self.process_chat,
                                dbus_interface="im.pidgin.purple.PurpleInterface",
                                signal_name="ReceivedChatMsg")
        self.bus.add_signal_receiver(self.process_im,
                                dbus_interface="im.pidgin.purple.PurpleInterface",
                                signal_name="ReceivedImMsg")
        obj = self.bus.get_object("im.pidgin.purple.PurpleService", "/im/pidgin/purple/PurpleObject")
        self.purple = dbus.Interface(obj, "im.pidgin.purple.PurpleInterface")
        self.htmlparser = HTMLParser()
        self.im_last_notify = {} # Sender Name -> datetime

    def run(self):
        self.loop = gobject.MainLoop()
        self.loop.run()

    def process_chat(self, account, sender, message, conversation, flags):
        self.process_message(account, sender, message, conversation, flags, type='chat')

    def process_im(self, account, sender, message, conversation, flags):
        self.process_message(account, sender, message, conversation, flags, type='im')
        
    def process_message(self, account, sender, message, conversation, flags, type):
        room = self.purple.PurpleConversationGetTitle(conversation)
        logging.info("user: %s, room: %s, flags: %s, said: %s" % (sender, room, flags, message))
        message = self.htmlparser.unescape(message)
        if MENTION_REGEX.search(message):
            cmd = MENTION_NOTIFY_CMD.format(
                sender=sender,
                room=room,
                message=message.replace('"', '\"'))
            if room not in IGNORE_CHANNEL:
                self.notify(cmd)
                self.android_notification(type, sender, message, room)
        elif type == 'im':
            cmd = IM_NOTIFY_CMD.format(
                sender=room,
                message=message.replace('"', '\"'))
            # Don't spam me everytime a user im's me, only notify me
            # if they have been silent for a while:
            last_msg_date = self.im_last_notify.get(room, datetime(1900,1,1))
            self.im_last_notify[room] = datetime.now()
            if (datetime.now() - last_msg_date).total_seconds() > NOTIFY_SPAM_INTERVAL:
                self.notify(cmd)
                self.android_notification(type, sender, message, room)

    def notify(self, cmd):
        self.kill_notifications()
        logging.debug(cmd)
        self._nag_process = subprocess.Popen(shlex.split(cmd))

    def kill_notifications(self):
        if self._nag_process:
            self._nag_process.kill()

    def android_notification(self, type, sender, message, room, priority=0):
        params = {'message': message, 'priority':priority,
                  'token': self.config.get('pushover','apikey'),
                  'user': self.config.get('pushover','userkey')}
        if type == 'im':
            params['title'] = "%s messaged you." % room #room is better name than sender
        elif type=='chat':
            params['title'] = "%s mentioned you in %s" % (sender, room)
        data = urlencode(params)
        request = Request('https://api.pushover.net/1/messages.json', data)
        u = urlopen(request)
        return u.read()

    def __get_config(self):
        config_path = os.path.join(os.path.expanduser('~'), '.pidgin_notifier')
        if not os.path.isfile(config_path):
            raise Exception(
                'No config file was found. Create %s and try again.'
                '. Make sure to chmod 600.'
                % config_path)
        if not oct(os.stat(config_path)[os.path.stat.ST_MODE]).endswith('00'):
            raise Exception(
                'Config file is not protected. Please run: '
                'chmod 600 %s' % config_path)
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        return config

if __name__ == "__main__":
    notifier = Notifier()
    notifier.run()
