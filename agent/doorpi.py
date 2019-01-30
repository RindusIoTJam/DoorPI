import json

from gpiozero import Button
from signal import pause


def handle_ring(config):
    print "RING to " + config['API_URL']


def open_door(config):
    print "OPEN"


def load(filename):
    """
        Loads a JSON file and returns a config .
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
