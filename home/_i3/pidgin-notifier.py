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


################################################################################
### Configure these to your liking:
################################################################################
NOTIFY_REGEX = re.compile('ryan', re.IGNORECASE)
NOTIFY_CMD = "i3-nagbar -m \"{sender} mentioned you in {room} : {message}\" -t warning -b 'Focus IM' 'i3-msg workspace im; killall i3-nagbar'"
################################################################################

class Notifier(object):
    "Manage notifications"
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self._nag_process = None
        self.bus.add_signal_receiver(self.process_message,
                                dbus_interface="im.pidgin.purple.PurpleInterface",
                                signal_name="ReceivedChatMsg")
        self.bus.add_signal_receiver(self.process_message,
                                dbus_interface="im.pidgin.purple.PurpleInterface",
                                signal_name="ReceivedImMsg")
        obj = self.bus.get_object("im.pidgin.purple.PurpleService", "/im/pidgin/purple/PurpleObject")
        self.purple = dbus.Interface(obj, "im.pidgin.purple.PurpleInterface")
        self.htmlparser = HTMLParser()

    def run(self):
        self.loop = gobject.MainLoop()
        self.loop.run()
        
    def process_message(self, account, sender, message, conversation, flags):
        logging.info("%s said: %s" % (sender, message))
        message = self.htmlparser.unescape(message)
        if NOTIFY_REGEX.search(message):
            self.notify(sender, message, conversation)

    def notify(self, sender, message, conversation):
        self.kill_notifications()
        room = self.purple.PurpleConversationGetTitle(conversation)
        message = message.replace('"', '\"')
        if room == sender:
            room = "IM"
        cmd = NOTIFY_CMD.format(
            sender=sender,
            room=room,
            message=message,
            notifier_pid=os.getpid())
        logging.debug(cmd)
        self._nag_process = subprocess.Popen(shlex.split(cmd))

    def kill_notifications(self):
        if self._nag_process:
            self._nag_process.kill()

if __name__ == "__main__":
    notifier = Notifier()
    notifier.run()
