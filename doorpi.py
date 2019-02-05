import calendar
import json
import os
import random
import string
import time
import urllib2
import BaseHTTPServer

from jinja2 import Template
from urlparse import parse_qs

# TODO: Remove development hack
emulation = True

try:
    from gpiozero import Button, DigitalOutputDevice
except ImportError:
    emulation = True

try:
    import ssl
except ImportError:
    print "ERROR: no ssl support"

config = None
door = None


def handle_ring(simulated=False):
    """
        Connects to the API to signal a ring and waits for a timeout for further commands.
    """
    global config

    if simulated is True:
        config['DOORPI_LAST_RING'] = "%s (Simulated)" % date_time_string()
    else:
        config['DOORPI_LAST_RING'] = "%s" % date_time_string()

    config['DOORPI_RING_TIMESTAMP'] = "%s" % calendar.timegm(time.gmtime())

    r = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(2)) + \
        "%s" % calendar.timegm(time.gmtime())

    config['DOORPI_RANDOM'] = r
    post_to_slack('@here RING, click <%s/%s|HERE> to open.' % (config['SLACK_OPENURL'], r))


def post_to_slack(text):
    """
        Connects to the API to signal a ring and waits for a timeout for further commands.
    """
    global config

    try:
        payload = {
            'text':       '%s' % text,
            'channel':    '%s' % config['SLACK_CHANNEL'],
            'username':   '%s' % config['DOOR_NAME'],
            'icon_emoji': ':door:',
            'link_names': 1,
            "attachments": [
            ]
        }
        req = urllib2.Request('https://hooks.slack.com/services/%s' % config['SLACK_WEBHOOK'],
                              data=json.dumps(payload),
                              headers={'Content-Type': 'application/json'})
        response = urllib2.urlopen(req, timeout=10)
        print '%s - slack response: %s' % (date_time_string(), response.getcode())

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            pass


def slack_open_door(request):
    open_door(True)
    request.do_GET()


def open_door(slack=False):
    """
        Will open the door.
    """
    global config
    global door

    config['DOORPI_RANDOM'] = '_'

    if (calendar.timegm(time.gmtime()) - int(config['DOORPI_RING_TIMESTAMP'])) <= int(config['OPEN_TIMEOUT']):

        if slack is True:
            print "%s - LOCAL OPEN (SLACK)" % date_time_string()
            config['DOORPI_LAST_OPEN'] = "%s (Slack)" % date_time_string()
        else:
            print "%s - LOCAL OPEN (WUI)" % date_time_string()
            config['DOORPI_LAST_OPEN'] = "%s (Local)" % date_time_string()

        post_to_slack("Door opened ....")

        # TODO: Open the door by flipping a GPIO pin on the PI
        if not emulation:
            door.on()
            time.sleep(1)
            door.off()
    else:
        print "%s - OPEN TIMEOUT EXCEEDED" % date_time_string()

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


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def do_POST(self):
        content_len = int(self.headers.getheader('content-length', 0))
        message = parse_qs(self.rfile.read(content_len))
        try:
            if message['ring'] is not None:
                print "%s - RING SIMULATION" % self.date_time_string()
                handle_ring(True)
        except KeyError:
            pass
        try:
            if message['open'] is not None:
                open_door()
        except KeyError:
            pass
        self.do_GET()

    def do_GET(self):
        global config

        if self.path == '/open/%s' % config['DOORPI_RANDOM']:
            slack_open_door(self)
            return

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if self.path == '/favicon.ico':
            return

        # TODO: Use Jinja2
        with open('doorpi.html') as file_:
            template = Template(file_.read())

        self.wfile.write( template.render(config=config, now=self.date_time_string()))


    def log_message(self, log_format, *args):
        # overwritten to suppress any output
        return


def main():
    """
        Does the basic setup and handles a ring.
    """
    global config
    global emulation
    global door

    config = load('doorpi.json')
    config['DOORPI_RANDOM'] = '_'

    if os.path.isfile('local_settings.json'):
        config.update(load('local_settings.json'))

    # TODO: Remove development hack (maybe)
    if not emulation:
        door = DigitalOutputDevice(int(config['GPIO_OPEN']))
        ring = Button(int(config['GPIO_RING']), hold_time=0.25)
        ring.when_pressed = handle_ring

    server_class = BaseHTTPServer.HTTPServer

    httpd = server_class((config['AGENT_HOST'], int(config['AGENT_PORT'])), RequestHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()


if __name__ == "__main__":
    main()
