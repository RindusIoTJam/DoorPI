import json
import os
import schedule
import threading
import time
import urllib2
import BaseHTTPServer

from urlparse import parse_qs

# TODO: Remove development hack
emulation = False
try:
    from gpiozero import Button
except:
    emulation = True

try:
    import ssl
except ImportError:
    print "ERROR: no ssl support"

config = None


def handle_ring(simulated=False):
    """
        Connects to the API to signal a ring and waits for a timeout for further commands.
    """
    global config
    if simulated is True:
        config['LAST_RING'] = "%s (Simulated)" % date_time_string()
    else:
        config['LAST_RING'] = "%s" % date_time_string()

    try:
        headers = {
            'X-Door-Id': config['DOOR_ID'],
            'X-Api-Key': config['API_KEY']
        }
        req = urllib2.Request(config['API_URL']+"/ring", None, headers)
        response = urllib2.urlopen(req, timeout=int(config['DOOR_TO']))
        print '%s - ring response code: %s' % (response.info().getheader('Date'), response.getcode())

        if response.getcode() == 200:
            open_door()

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            pass


def open_door(local=False):
    """
        Will open the door.
    """
    global config

    if local is True:
        print "%s - LOCAL OPEN" % date_time_string()
        config['LAST_OPEN'] = "%s (Local)" % date_time_string()
        # TODO: Send event to manager to record that door was opened locally by agent wui.
    else:
        print "%s - REMOTE OPEN " % date_time_string()
        config['LAST_OPEN'] = "%s (Remote)" % date_time_string()

    # TODO: Open the door by flipping a GPIO pin on the PI


def load(filename):
    """
        Loads a JSON file and returns a config.
    """
    with open(filename, 'r') as settings_file:
        _config = json.load(settings_file)

    return _config


def heartbeat():
    """
        Connects to the API to signal a heartbeat.
    """
    global config
    try:
        headers = {
            'X-Door-Id': config['DOOR_ID'],
            'X-Api-Key': config['API_KEY']
        }
        req = urllib2.Request(config['API_URL']+"/ping", None, headers)
        response = urllib2.urlopen(req, timeout=5)
        print '%s - ping response code: %s' % (response.info().getheader('Date'), response.getcode())

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            raise


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


class HeartbeatThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.ping = True

    def run(self):
        schedule.every(5).minutes.do(heartbeat)
        while self.ping:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self.ping = False


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
                open_door(True)
        except KeyError:
            pass
        self.do_GET()

    def do_GET(self):
        global config
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        if self.path == '/favicon.ico':
            return
        self.wfile.write("<html>"
                         "<body>"
                         "<h1>%s</h1>" % config['DOOR_ID'] +
                         "<table border='0'>"
                         "<tr><td>Current time: </td><td>%s</td></tr>" % self.date_time_string())

        try:
            self.wfile.write("<tr><td>Last ring:    </td><td>%s</td></tr>" % config['LAST_RING'])
        except KeyError:
            self.wfile.write("<tr><td>Last ring:    </td><td>unknown</td></tr>")

        try:
            self.wfile.write("<tr><td>Last open:    </td><td>%s</td></tr>" % config['LAST_OPEN'])
        except KeyError:
            self.wfile.write("<tr><td>Last open:    </td><td>unknown</td></tr>")

        self.wfile.write("</table>"
                         "<form action='/' method='post'>")
        self.wfile.write("<input type='submit' value='reload page' name='reload'/>")
        # TODO: Remove development hack
        if emulation:
            self.wfile.write("<input type='submit' value='simulate ring' name='ring'/>")
        self.wfile.write("<input type='submit' value='open door' name='open'/>"
                         "</form>"
                         "</body>"
                         "</html>"
                         )

    def log_message(self, format, *args):
        return


def main():
    """
        Does the basic setup and handles a ring.
    """
    global config
    global emulation

    config = load('doorpi.json')

    if os.path.isfile('local_settings.json'):
        config.update(load('local_settings.json'))

    heartbeat()

    # TODO: Remove development hack
    if not emulation:
        ring = Button(2, hold_time=0.25)
        ring.when_pressed = handle_ring

    heartbeat_thread = HeartbeatThread()
    heartbeat_thread.start()

    server_class = BaseHTTPServer.HTTPServer

    httpd = server_class((config['AGENT_HOST'], int(config['AGENT_PORT'])), RequestHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()
    heartbeat_thread.stop()


if __name__ == "__main__":
    main()
