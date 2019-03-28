import datetime
import json
import logging
import time
import urllib.request

from typing import Optional, Awaitable

from .doorphone import DoorPhone, SIMULATION

import tornado.escape
import tornado.template
import tornado.web
import tornado.websocket
import validators


class HttpHandler(tornado.web.RequestHandler):
    """ Handles open request to / and /simulation """

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self, path=None) -> None:
        if (SIMULATION or self.application.get('simulation')) and path == 'simulation':
            self.render("simulation.html", app=self.application)
        else:
            self.render("index.html", app=self.application)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """ Handles WebSocket communication on /door """

    waiters = set()

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def __init__(self, *args, **kwargs) -> None:
        super(WebSocketHandler, self).__init__(*args, **kwargs)

    def get_compression_options(self) -> dict:
        # Non-None enables compression with default options.
        return {}

    def open(self) -> None:
        WebSocketHandler.waiters.add(self)
        logging.info('Client IP: %s connected. Total clients: %s' % (self.request.remote_ip,
                                                                     len(WebSocketHandler.waiters)))

        message = {
            "action": "update",
            "last_open": "%s" % self.application.get('last.open'),
            "last_ring": "%s" % self.application.get('last.ring'),
            "timestamp": "%s" % time.time()
        }

        self.write_message(message)

    def on_close(self) -> None:
        WebSocketHandler.waiters.remove(self)
        logging.info('Client IP: %s disconnected. Total clients: %s' % (self.request.remote_ip,
                                                                        len(WebSocketHandler.waiters)))

    def on_message(self, message) -> None:
        logging.info("got message %s from %s", message, self.request.remote_ip)
        payload = tornado.escape.json_decode(message)

        payload.update({
            "timestamp": "%s" % time.time()
        })

        if payload['action'] == "open":
            DoorPhone.instance().open_door(payload.get('secret'))
        elif payload['action'] == "simulate_ring":
            if SIMULATION or self.application.get('simulation'):
                DoorPhone.instance().timeout = 10
                DoorPhone.instance().simulate_ring()

    @classmethod
    def send_update(cls, message) -> None:
        logging.debug("sending message %s to %d waiters" % (message, len(cls.waiters)))
        for waiter in cls.waiters:
            try:
                waiter.write_message(message)
            except RuntimeError as err:
                logging.error("Error sending message: %s" % str(err), exc_info=True)


class SlackHandler(tornado.web.RequestHandler):
    """ Handles posting a Slack message and open requests coming in by HTTP URL /slack/{secret-key} """

    loader = None
    valid = None

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self, secret=None) -> None:
        """
        Handles GET request to /slack/{secret}

        :param secret: Everything in query_path behind /slack/
        :type secret: str
        """
        if DoorPhone.instance().open_door(secret):
            self.render("slack.html", app=self.application, opened=True)
        else:
            self.render("slack.html", app=self.application, opened=False)

    @classmethod
    def validate(cls, application: "Application") -> bool:
        if cls.valid is None:
            cls.valid = False
            try:
                if not validators.url(application.get("slack.webhook")):
                    raise ValueError("slack.webhook doesn't validate as URL")

                if not validators.url(application.get("slack.baseurl")):
                    raise ValueError("slack.baseurl doesn't validate as URL")

                if application.get("slack.baseurl")[-1] == '/':
                    application.set("slack.baseurl", application.get("slack.baseurl")[0:-1])
                    logging.info("removed trailing '/' from slack.baseurl")

                cls.valid = True
            except KeyError as err:
                logging.warning("Slack deactivated because minimum setup is incomplete or incorrect: %s" % str(err))
            except ValueError as err:
                logging.warning("Slack deactivated because minimum setup is incomplete or incorrect: %s" % str(err))

        return cls.valid

    @classmethod
    def send(cls, application: "Application", template_file: str, text: str, secret=None) -> None:
        """

        :param application: The calling application
        :param template_file: The message template
        :param text: The message text
        :param secret: The secret key
        :type application: Application
        :type template_file: str
        :type text: str
        :type secret: str
        """

        if cls.valid:

            if cls.loader is None:
                cls.loader = tornado.template.Loader(application.settings.get("template_path"), autoescape=None)

            try:
                req = urllib.request.Request(application.get("slack.webhook"),
                                             data=cls.loader.load(template_file).generate(app=application,
                                                                                          text=text,
                                                                                          secret=secret),
                                             headers={'Content-Type': 'application/json'})
                response = urllib.request.urlopen(req, timeout=10)
                logging.info("Slack responded: %s on message '%s'", response.getcode(), text)

            except IOError as e:
                logging.info("can't connect, reason: %s" % str(e))


class ApiHandler(tornado.web.RequestHandler):
    """ Handles open requests coming in by HTTP URL /api/{api-key} """

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self, api_key=None) -> None:
        """
        Handles GET request to /api/{api-key}

        :param api_key: Everything in query_path behind /api/
        :type api_key: str
        """
        if self.valid_api_key(api_key):
            response = {'open': "%s" % time.time()}
            DoorPhone.instance()._api_open_door()
            logging.warning("API open for %s (%s)" % (api_key, self.request.remote_ip))
        else:
            response = {'error': "Unauthorized"}
            self.set_status(401)

        self.set_header('Content-Type', 'text/json')
        self.write(response)
        self.finish()

    def valid_api_key(self, api_key=None):
        """
        Check if a given apikey is valid for opening the door and in case
        of usage of an one-time ("type": "once") apikey invalidating by
        recording the key in the file usedkeys.json.

        :param api_key: The apikey to test
        :type api_key: str
        :return: True is valid, False in invalid
        :rtype: bool
        """

        if api_key in self.application.door_api_keys:

            api_key_type = self.application.door_api_keys.get(api_key).get("type")

            if api_key_type == "master":
                return True
            else:
                # check if is Mo-Fr
                if datetime.datetime.today().weekday() > 4:
                    return False

                # check 07:00-18:00
                hour = datetime.datetime.today().hour
                if hour < 7 or hour > 18:
                    return False

                if api_key_type == "restricted":
                    return True

                # check if date is in range
                if datetime.datetime.strptime(self.application.door_api_keys.get(api_key).get("from"),
                                              "%d.%m.%Y").date() \
                        <= datetime.datetime.today().date() \
                        <= datetime.datetime.strptime(self.application.door_api_keys.get(api_key).get("till"),
                                                      "%d.%m.%Y").date():

                    if api_key_type == "limited":
                        return True

                    elif api_key_type == "once":
                        try:
                            with open('apikeys_used.json', 'r') as keys_file:
                                used = json.load(keys_file)
                        except IOError:
                            used = {}

                        if api_key in used:
                            logging.warning("one-time key already used.")
                            return False

                        used.update({"%s" % api_key: "%s" % time.time()})

                        with open('apikeys_used.json', 'w') as keys_file:
                            json.dump(used, keys_file)

                        logging.warning("one-time key invalidated.")
                        return True

        return False
