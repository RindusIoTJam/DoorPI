import json
import logging
import os.path
import requests
import signal
import sys
import time

import tornado.escape
import tornado.ioloop
import tornado.web

logging.basicConfig(level=logging.DEBUG)

from core.doorphone import DoorPhone
from core.callbacks import Callback
from core.handlers import HttpHandler, WebSocketHandler, SlackHandler, ApiHandler

app = None


class Application(tornado.web.Application, Callback):
    """
    The main Application
    """

    door_phone = None
    door_settings = {}
    door_api_keys = {}

    def __init__(self) -> None:
        """
        Init method
        """

        # order matters
        handlers = [
            (r"/api/open/(.*)", ApiHandler),
            (r"/door", WebSocketHandler),
            (r"/slack/(.*)", SlackHandler),
            (r"/(.*)", HttpHandler)
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            compiled_template_cache=False,
            static_hash_cache=False,
            serve_traceback=True
        )

        self.load_settings()
        super(Application, self).__init__(handlers, **settings)

    def set(self, key: str, value=None)-> None:
        self.door_settings.update({"doorpi.%s" % key: value})

    def get(self, key: str, default=None):
        return self.door_settings.get("doorpi.%s" % key, default)

    @staticmethod
    def load(filename: str) -> dict:
        """
        Loads a JSON file and returns a dict.

        :param filename: The filename to load
        :type filename: str
        :return: A dictionary
        :rtype: dict
        """
        _dict = {}

        try:
            with open(filename, 'r') as file:
                _dict = json.load(file)
        except IOError as err:
            logging.warning(str(err))

        return _dict

    def load_settings(self, signum=None, frame=None) -> None:
        """
        Reloads configuration on sigusr1 (systemctl reload doorpi-agent.service)

        :param signum: signature parameter
        :param frame: signature parameter
        """
        self.door_settings.update(Application.load('main.json'))
        self.door_settings.update(Application.load('local_settings.json'))
        self.door_api_keys.update(Application.load('apikeys.json'))
        if signum is None:
            self.door_settings.update(Application.load('last.json'))
        if not self.get('last.ring'):
            self.set('last.ring', '')
        if not self.get('last.open'):
            self.set('last.open', '')

    def ring_callback(self, secret_key: str, first_ring: bool, follow_up: bool) -> None:
        """
        Handle a ring event

        :param secret_key: The key to open
        :param first_ring: True if first ring
        :param follow_up: True if follow-up ring within timeout
        :type secret_key: str
        :type first_ring: bool
        :type follow_up: bool
        """
        logging.debug("RINGCALLBACK for %s" % self.get('door.name'))
        timestamp = time.time()
        self.set('last.ring', "%s" % timestamp)

        # Inform WebSocket Clients
        payload = ({
            "action": "ring",
            "secret": "%s" % secret_key,
            "timestamp": "%s" % timestamp
        })
        WebSocketHandler.send_update(tornado.escape.json_encode(payload))

        # Inform Slack
        if SlackHandler.validate(self):
            if first_ring:
                SlackHandler.send(self, "slack_1st_ring.json", "@here *DING DONG*", secret_key)
            else:
                SlackHandler.send(self, "slack_ring.json", "*DING DONG* ... *DING DONG*", secret_key)

    def timeout_callback(self, runtime: int) -> None:
        """
        Handle a timeout event

        :param runtime: time in seconds from first ring
        :type runtime: int
        """
        logging.debug("TIMEOUTCALLBACK for %s after %s seconds" % (self.get('door.name'), runtime))
        timestamp = time.time()

        # Inform WebSocket Clients
        payload = ({
            "action": "timeout",
            "timestamp": "%s" % timestamp
        })
        WebSocketHandler.send_update(tornado.escape.json_encode(payload))

        # Inform Slack
        if SlackHandler.validate(self):
            SlackHandler.send(self, "slack_timeout.json", "Door wasn't opened after %s seconds." % runtime)

        # Inform ThingSpeak
        if self.get('thingspeak.writeAPIKey') and self.get('thingspeak.field.timeout'):
            requests.get('https://api.thingspeak.com/update.json?api_key=%s&%s=%s' %
                         (self.get('thingspeak.writeAPIKey'), self.get('thingspeak.field.timeout'), runtime))

    def open_callback(self, runtime: int) -> None:
        """
        Handle a open event

        :param runtime: time in seconds from first ring
        :type runtime: int
        """
        logging.debug("OPENCALLBACK for %s after %s seconds" % (self.get('door.name'), runtime))
        timestamp = time.time()
        self.set('last.open', "%s" % timestamp)

        # Inform WebSocket Clients
        payload = ({
            "action": "open",
            "timestamp": "%s" % timestamp
        })
        WebSocketHandler.send_update(tornado.escape.json_encode(payload))

        # Inform Slack
        if SlackHandler.validate(self):
            SlackHandler.send(self, "slack_open.json", "Door was opened after %s seconds." % runtime)

        # Inform ThingSpeak
        if self.get('thingspeak.writeAPIKey') and self.get('thingspeak.field.open'):
            requests.get('https://api.thingspeak.com/update.json?api_key=%s&%s=%s' %
                         (self.get('thingspeak.writeAPIKey'), self.get('thingspeak.field.open'), runtime))


def handle_sigterm(signum=None, frame=None):
    """
    Saves current state on sigterm (systemctl stop doorpi-agent.service)
    end exists.

    :param signum: signature parameter
    :param frame: signature parameter
    """
    global app
    with open('last.json', 'w') as file:
        json.dump({
            "doorpi.last.open": "%s" % app.get('last.open'),
            "doorpi.last.ring": "%s" % app.get('last.ring')
        }, file)

    if DoorPhone.instance().timeout_thread is not None:
        logging.debug("Stopping running DoorPhone.timeout_thread")
        DoorPhone.instance().timeout_thread.stop()

    tornado.ioloop.IOLoop.current().stop()

    # Inform Slack
    if SlackHandler.validate(app):
        SlackHandler.send(app, "slack_doorpi.json", "DoorPI stopped")

    sys.exit(0)


def main():
    """
    Main entry point
    """
    global app

    app = Application()

    DoorPhone(callback=app,
              gpio_ring=int(app.get('gpio.ring', default=24)),
              gpio_open=int(app.get('gpio.open', default=23)))

    signal.signal(signal.SIGUSR1, app.load_settings)
    signal.signal(signal.SIGTERM, handle_sigterm)

    app.listen(port=app.get('listen.port'))

    # Inform Slack
    if SlackHandler.validate(app):
        SlackHandler.send(app, "slack_doorpi.json", "DoorPI started (%s)" % app.get('slack.baseurl'))

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        handle_sigterm()


if __name__ == "__main__":
    """ DoorPI Application """
    main()
    """
    th = TestHandler()
    x = DoorPhone(ring_callback=th, timeout_callback=th)
    time.sleep(1)
    x.open_door("-")
    x.simulate_ring()
    time.sleep(1)
    x.simulate_ring()
    """
