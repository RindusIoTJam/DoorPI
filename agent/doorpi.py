import json
import schedule
import time
import urllib2

from gpiozero import Button

try:
    import ssl
except ImportError:
    print "ERROR: no ssl support"


def handle_ring():
    """
        Connects to the API to signal a ring and waits for a timeout for further commands.
    """
    config = load('doorpi.json')
    try:
        headers = {
            'X-Door-Id': config['DOOR_ID'],
            'X-Api-Key': config['API_KEY']
        }
        req = urllib2.Request(config['API_URL']+"/ring", None, headers)
        response = urllib2.urlopen(req)
        print 'response headers: "%s"' % response.info()

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
    config = load('doorpi.json')


def load(filename):
    """
        Loads a JSON file and returns a config.
    """
    with open(filename, 'r') as settings_file:
        config = json.load(settings_file)
    return config


def heartbeat():
    """
        Connects to the API to signal a heartbeat.
    """
    config = load('doorpi.json')
    try:
        headers = {
            'X-Door-Id': config['DOOR_ID'],
            'X-Api-Key': config['API_KEY']
        }
        req = urllib2.Request(config['API_URL']+"/ping", None, headers)
        response = urllib2.urlopen(req)
        print 'response headers: "%s"' % response.info()

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
    schedule.every(5).minutes.do(heartbeat)

    ring = Button(12, pull_up=True, bounce_time=60, hold_time=0.25)
    ring.when_pressed = handle_ring()

    while True:
        schedule.run_pending()
        time.sleep(5)


if __name__ == "__main__":
    main()
