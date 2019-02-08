import calendar
import json
import logging
import os.path
import random
import string
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.template
import tornado.web
import tornado.websocket
import threading
import time
import urllib2
import validators

# TODO: Remove development hack (maybe)
emulation = False

try:
    from gpiozero import Button, DigitalOutputDevice
except ImportError:
    emulation = True


class Application(tornado.web.Application):
    _config = None
    _slack  = None

    def __init__(self):
        handlers = [(r"/", MainHandler),
                    (r"/slack", SlackHandler),
                    (r"/door",  DoorSocketHandler)]
        settings = dict(
            cookie_secret=Application.config('webui.cookie.secret'),
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        super(Application, self).__init__(handlers, **settings)
        print "Application started. Emulation=%s" % emulation

    @classmethod
    def set_config(cls, config):
        Application._config = Application.__config__(config)

    @classmethod
    def config(cls, key=None):
        try:
            return Application._config[key]
        except KeyError:
            return Application._config

    @classmethod
    def __config__(cls, _config):
        """
           Check essential config settings, use default if unset

        :param _config:
        """
        defaults = (("webui.port", "8080"),
                    ("webui.cookie.secret", "__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE__"),
                    ("door.name", "Door"),
                    ("door.open.timeout", "60"),
                    ("gpio.ring", "18"),
                    ("gpio.open", "23"))
        for setting, default in defaults:
            try:
                _config[setting]
            except KeyError:
                _config[setting] = default

        # Empty last ring and open, make persistent maybe later
        _config['_door.last.ring'] = ''
        _config['_door.last.open'] = ''

        if os.path.isfile('local_settings.json'):
            _config.update(load('local_settings.json'))

        return _config

    @classmethod
    def has_valid_slack_config(cls, _config):
        """
           Check essential config settings for Slack

        :param _config:
        :return: True is setup is valid, False otherwise
        """
        if Application._slack is None:
            Application._slack = False
            try:
                if not validators.url(_config["slack.webhook"]):
                    logging.warn("slack.webhook doesn't validate as URL")

                if not validators.url(_config["slack.baseurl"]):
                    logging.warn("slack.baseurl  doesn't validate as URL")

                if _config["slack.baseurl"][-1] == '/':
                    _config["slack.baseurl"] = _config["slack.baseurl"][0:-1]
                    logging.info("removed trailing '/' from slack.baseurl")

                Application._slack = True
            except KeyError:
                Application._slack = False
                logging.warn("Slack deactivated because setup for Slack is incomplete or incorrect.")

        return Application._slack

class SlackHandler(tornado.web.RequestHandler):
    loader = None

    def get(self):
        self.render("index.html", config=Application.config(), emulation=emulation)

    @classmethod
    def send(cls, text):

        if Application.has_valid_slack_config(Application.config()):

            template_file = 'slack.json'
            try:
                message = SlackHandler.loader.load(template_file).generate(channel=Application.config('slack.channel'),
                                                                           username=Application.config('door.name'),
                                                                           text=text)
            except AttributeError:
                SlackHandler.loader = tornado.template.Loader(os.path.join(os.path.dirname(__file__), "templates"),
                                                              autoescape=None)
                message = SlackHandler.loader.load(template_file).generate(channel=Application.config('slack.channel'),
                                                                           username=Application.config('door.name'),
                                                                           text=text)
            try:
                req = urllib2.Request(Application.config('slack.webhook'),
                                      data=message,
                                      headers={'Content-Type': 'application/json'})
                response = urllib2.urlopen(req, timeout=10)
                logging.info("Slack responded: %s on message '%s'", response.getcode(), text)

            except IOError, e:
                if hasattr(e, 'code'):  # HTTPError
                    print 'http error code: ', e.code
                elif hasattr(e, 'reason'):  # URLError
                    print "can't connect, reason: ", e.reason
                else:
                    pass


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", config=Application.config(), emulation=emulation)


class DoorSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    door = None
    ring = None

    timeout_thread = None

    def __init__(self, *args, **kwargs):
        # TODO: Remove development hack (maybe)
        global emulation
        if not emulation:
            DoorSocketHandler.door = DigitalOutputDevice(int(Application.config('gpio.open')))
            DoorSocketHandler.ring = Button(int(Application.config('gpio.ring')), hold_time=0.25)
            DoorSocketHandler.ring.when_pressed = DoorSocketHandler.handle_ring

        super(DoorSocketHandler, self).__init__(*args, **kwargs)

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        logging.info('Client IP: %s connected.' % self.request.remote_ip)
        DoorSocketHandler.waiters.add(self)

    def on_close(self):
        logging.info('Client IP: %s disconnected.' % self.request.remote_ip)
        DoorSocketHandler.waiters.remove(self)

    def on_message(self, message):
        logging.info("got message %s from %s", message, self.request.remote_ip)
        payload = tornado.escape.json_decode(message)

        payload.update({
            "timestamp": "%s" % time.time()
        })

        if payload['action'] == "ring":
            secret = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(2)) + \
                     "%s" % calendar.timegm(time.gmtime())

            Application.config()['_door.open.secret'] = secret
            payload.update({
                "secret": "%s" % secret
            })
            DoorSocketHandler.send_update(tornado.escape.json_encode(payload))
            self.handle_ring(secret)

        if payload['action'] == "open":
            try:
                if payload['secret'] == Application.config().pop('_door.open.secret', None):
                    DoorSocketHandler.send_update(tornado.escape.json_encode(payload))
                    self.handle_open()
                else:
                    logging.info("ignoring OPEN without correct ring secret")
            except KeyError:
                logging.info("ignoring OPEN without any secret given")

    @classmethod
    def handle_ring(cls, secret):
        """
           Handle a ring event by enabling the _Open Door_ button for a given time
        """
        logging.info("handling RING")

        if DoorSocketHandler.timeout_thread is None:
            # Start a thread enabling open button for door.open.timeout seconds
            DoorSocketHandler.timeout_thread = TimeoutThread(timeout=int(Application.config('door.open.timeout')))
            DoorSocketHandler.timeout_thread.start()
        else:
            # Extend the time if another ring occurs
            DoorSocketHandler.timeout_thread.extend()

        if Application.has_valid_slack_config(Application.config()):
            SlackHandler.send('@here DING DONG :: open >>> <%s/slack?%s|HERE> <<<' % (Application.config('slack.baseurl'), secret))

    @classmethod
    def handle_open(cls):
        """
           Handle a open event by disabling the _Open Door_ button and flipping the GPIO open pin
        """
        if DoorSocketHandler.timeout_thread is None:
            logging.info("ignoring OPEN without prior ring")
            return

        logging.info("handling OPEN")

        DoorSocketHandler.timeout_thread.stop()
        if not emulation:
            DoorSocketHandler.door.on()

        if Application.has_valid_slack_config(Application.config()):
            SlackHandler.send('@here DoorPI has opened the door.')

        if not emulation:
            time.sleep(0.5)
            DoorSocketHandler.door.off()


    @classmethod
    def send_update(cls, message):
        logging.info("sending message to %d waiters", len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)


class TimeoutThread (threading.Thread):
    def __init__(self, timeout=60):
        threading.Thread.__init__(self)
        self.timeout = timeout
        self.finish = int(time.time())+timeout
        self.wait = True

    def run(self):
        """
            Wait for timeout to occur and s
        """
        while self.wait and int(time.time()) < self.finish:
            time.sleep(1)
            logging.info("remaining time to open: %s seconds" % (self.finish - int(time.time())))
        if self.wait:
            DoorSocketHandler.send_update({"action": "timeout"})

    def extend(self):
        """
            Loads a JSON file and returns a config.
        """
        self.finish += self.timeout

    def stop(self):
        """
            Loads a JSON file and returns a config.
        """
        self.wait = False


def load(filename):
    """
        Loads a JSON file and returns a config.
    """
    with open(filename, 'r') as settings_file:
        _config = json.load(settings_file)

    return _config


def date_time_string(timestamp=None):
    """
        Return the current date and time formatted for a message header.
    """
    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        weekdayname[wd],
        day, monthname[month], year,
        hh, mm, ss)
    return s


def main():

    config = load('doorpi.json')

    tornado.options.parse_command_line()

    Application.set_config(config)
    app = Application()

    app.listen(int(Application.config('webui.port')))

    if Application.has_valid_slack_config(Application.config()):
        SlackHandler.send('@here DoorPI started at %s' % Application.config('slack.baseurl'))

    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
