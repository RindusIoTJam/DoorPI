import json
import os
import schedule
import threading
import time
import urllib2
import BaseHTTPServer

from gpiozero import Button

try:
    import ssl
except ImportError:
    print "ERROR: no ssl support"

config = None


def handle_ring():
    """
        Connects to the API to signal a ring and waits for a timeout for further commands.
    """
    global config
    try:
        headers = {
            'X-Door-Id': config['DOOR_ID'],
            'X-Api-Key': config['API_KEY']
        }
        req = urllib2.Request(config['API_URL']+"/ring", None, headers)
        response = urllib2.urlopen(req)
        print '%s - ring response code: %s' % (response.info().getheader('Date'), response.getcode())

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            raise


def open_door():
    """
        Will open the door.
    """
    global config


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
        response = urllib2.urlopen(req)
        print '%s - ping response code: %s' % (response.info().getheader('Date'), response.getcode())

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            raise


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

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write("OK")

    def log_message(self, format, *args):
        return

def main():
    """
        Does the basic setup and handles a ring.
    """
    global config
    config = load('doorpi.json')

    if os.path.isfile('local_settings.json'):
        config = load('local_settings.json')

    heartbeat()

    ring = Button(2, hold_time=0.25)
    ring.when_pressed = handle_ring()

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
