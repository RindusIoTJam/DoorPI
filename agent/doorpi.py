import json
import schedule
import time
import urllib2

from gpiozero import Button

try:
    import ssl
except ImportError:
    print "ERROR: no ssl support"

config = None
COLORED = 1
UNCOLORED = 0


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
        print '%s - ring response code: %s' % (response.info().getparam('Date'), response.getcode())
        #print 'response headers: "%s"' % response.info()

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
        print '%s - ping response code: %s' % (response.info().getparam('Date'), response.getcode())
        #print 'response headers: "%s"' % response.info()

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            raise


def main():
    """
        Does the basic setup and handles a ring.
    """
    global config
    config = load('doorpi.json')

    schedule.every(5).minutes.do(heartbeat)
    handle_ring()

    ring = Button(2, pull_up=True, hold_time=0.25)
    ring.when_pressed = handle_ring()

    while True:
        schedule.run_pending()
        time.sleep(5)


if __name__ == "__main__":
    main()
