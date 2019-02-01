import epd2in13b
import json
import os
import schedule
import socket
import time
import urllib2

from epd2in13b import ROTATE_90
from gpiozero import Button
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from subprocess import check_output

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
        print 'response headers: "%s"' % response.info()

    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print 'http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "can't connect, reason: ", e.reason
        else:
            raise


def update_epaper(text):
    epd = epd2in13b.EPD()
    epd.init()
    epd.set_rotate(ROTATE_90)

    # clear the frame buffer
    frame_black = [0xFF] * (epd.width * epd.height / 8)
    frame_red   = [0xFF] * (epd.width * epd.height / 8)


    h1 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 20)
    h2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 16)

    epd.draw_filled_rectangle(frame_red, 0, 0, 212, 28, COLORED);
    commit = check_output(["git rev-parse --short HEAD"]).rstrip()
    epd.draw_string_at(frame_red, 7,  4, "DoorPI v.0.0.0-"+commit, h1, UNCOLORED)
    epd.draw_rectangle(frame_black, 0, 29, 212, 30, COLORED);

    if text is not None:
        epd.draw_string_at(frame_black, 15, 38, "Last ring: "+text, h2, COLORED)

    gw = os.popen("ip -4 route show default").read().split()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((gw[2], 0))
    ipaddr = s.getsockname()[0]
    epd.draw_string_at(frame_black, 15, 58, "NETIP: " + ipaddr, h2, COLORED)

    scanoutput = check_output(["iwgetid"])
    for line in scanoutput.split():
        ssid = line.split(':')[-1].replace('"', '')
    epd.draw_string_at(frame_black, 16, 78, "WLAN: " + ssid, h2, COLORED)

    # display the frames
    epd.display_frame(frame_black, frame_red)
    epd.sleep()


def main():
    """
        Does the basic setup and handles a ring.
    """
    global config
    config = load('doorpi.json')

    update_epaper(None)

    schedule.every(5).minutes.do(heartbeat)
    handle_ring()

    ring = Button(2, pull_up=True, hold_time=0.25)
    ring.when_pressed = handle_ring()

    while True:
        schedule.run_pending()
        time.sleep(5)


if __name__ == "__main__":
    main()
