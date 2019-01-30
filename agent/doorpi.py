import json
import urllib2

from signal import pause


try:
    from gpiozero import Button
except ImportError:
    print "ERROR: no gpiozero support"

try:
    import ssl
except ImportError:
    print "ERROR: no ssl support"


def handle_ring(config):
    """
        Connects to the API to signal a ring and waits for a timeout for further commands.
    """
    try:
        headers = {
            'X-Door-Id': config['DOOR_ID'],
            'X-Api-Key': config['API_KEY']
        }
        req = urllib2.Request(config['API_URL'], None, headers)
        response = urllib2.urlopen(req)
        print 'response headers: "%s"' % response.info()

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            raise

def open_door(config):
    """
        Will open the door.
    """


def load(filename):
    """
        Loads a JSON file and returns a config.
    """
    with open(filename, 'r') as settings_file:
        config = json.load(settings_file)
    return config


def main():
    """
        Does the basic setup and handles a ring.
    """
    config = load('doorpi.json')

    ring = Button(18, pull_up=True, bounce_time=60, hold_time=0.25)
    ring.when_pressed = handle_ring(config)
    pause()


if __name__ == "__main__":
    main()
