import json
import time
import BaseHTTPServer


config = None


class EventHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/plain")
        s.end_headers()

    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/plain")
        s.end_headers()
        s.wfile.write("OK")

    def log_message(s, format, *args):
        print s.headers.getheader('X-Door-Id', 'unknown')
        return


def load(filename):
    """
        Loads a JSON file and returns a config.
    """
    with open(filename, 'r') as settings_file:
        _config = json.load(settings_file)
    return _config


def main():
    """
        Does the basic setup and handles a ring.
    """
    global config
    config = load('manager.json')

    server_class = BaseHTTPServer.HTTPServer

    httpd = server_class((config['MANAGER_HOST'], int(config['MANAGER_PORT'])), EventHandler)
    print time.asctime(), "Server Starts - %s:%s" % (config['MANAGER_HOST'], config['MANAGER_PORT'])

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()
    print time.asctime(), "Server Stops - %s:%s" % (config['MANAGER_HOST'], config['MANAGER_PORT'])


if __name__ == "__main__":
    main()
