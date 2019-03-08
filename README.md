# [![AbstruseCI](http://iot.rindus.de:6499/badge/3)](http://iot.rindus.de:6499/repo/3) DoorPI

## Abstract

Use a RaspberryPi Zero W (rpi0w) to detect a ring at a remote door 
bell and open also the door remotely. 

## Prerequisites

- RaspberryPi Zero W w/ Raspbian installed, the to-be-build
  DoorPI-HAT (TODO) installed and connected to some wifi.
- git / python / pip / virtualenv installed on Raspbian.

### Optional

- Slack 'webhook access token' for [Slack](https://slack.com) integration
- Sentry DSN for [Sentry.io](https://sentry.io) integration

## Agent Installation

The agent sits near the bell with the physical door open button, 
detects a ring, sends a message to slack and eventually handles
a open-door event by flipping a relays.

Connect to the rpi0w by ssh and change to a directory where
you want the agent to reside, e.g. inside `/usr/local` with
the name doorpi-agent

```Bash
$ mkdir /usr/local/doorpi-agent
$ cd /usr/local/doorpi-agent
$ git clone https://github.com/RindusIoTJam/DoorPI.git .
$ virtualenv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

Now change the file `doorpi.json` to your needs and/or create a file
`local_settings.json` that has at least a unique `door.name` setting. 
See [Settings](../../../dooropener-Rpi0-#Settings) for more options.

_The file `doorpi.json` MUST exist and contain valid JSON_

```JSON
{
  "door.name": "OfficeDoor"
}
```

The agent can be started by executing `python doorpi.py` at the agent
installation directory and offers a web interface at the configured 
`webui.port`, by default [`http://0.0.0.0:8080`](http://0.0.0.0:8080)
meaning on all IP addresses claimed by the rpi0w.

### systemd service definition

Create a file `/etc/systemd/system/doorpi-agent.service` with content

```Properties
[Unit]
Description=DoorPi-Agent
After=multi-user.target

[Service]
Type=idle
WorkingDirectory=/usr/local/doorpi-agent
ExecStart=/usr/local/doorpi-agent/venv/bin/python doorpi.py

[Install]
WantedBy=multi-user.target
```

Change `WorkingDirectory` and `ExecStart` to your installation directory
and after save run

```Bash
chmod 664 /etc/systemd/system/doorpi-agent.service
systemctl daemon-reload
systemctl enable doorpi-agent.service
systemctl start doorpi-agent.service
```

to enable start-on-boot and to also start the service now.

### HTTPS
 
The agent installation itself doesn't handle secure connections. This can
e.g. be implemented with STunnel, Apache or NGINX. Please consult the 
corresponding setup for the tool you selected. The frontend will automatically
detect if it's running in a secure environment.

## Settings

At the agent installation directory you can create a `local_settings.json`
that is ignored by `.gitignore` to overwrite setup from `doorpi.json`. 
E.g.:

```JSON
{
  "door.name": "Test-Door",
  "door.open.timeout": 10
}
```

| JSON key        | Description |Default |
| --------------- | ----------- | ------ |
| `webui.port`    | Listen port of the agents web interface. | `8080` |
| `webui.cookie.secret` | | `__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE__` |
| `door.name`     | An identifier of this door agent. | `Door` |
| `door.open.timeout` | Timeout to accept an open response on a ring event. If another ring happens within timeout the remaining time extends with the same value. Value is given in seconds.| `60` |
| `gpio.open`     | GPIO out-pin where the door-open relay connects. | `23` |
| `gpio.ring`     | GPIO in-pin where the ring is detected. | `24` |
| `slack.webhook` | If set this webhook will be used to post a ring message to Slack | |
| `slack.channel` | Slack channel to post to. The default channel will be used if unset. | |
| `slack.baseurl` | BaseURL of DoorPI. Usually `http://door.acme.com:[webui.port]` | |
| `sentry.dsn` | For development purposes only. If it doesn't ring a bell, ignore this setting. ||

### Open API

By GET requesting in the form of `/api(open/{apikey}` the door can be opened 
without an upfront ring to e.g. use a mobile application like Android
[HTTP Request Widget](https://play.google.com/store/apps/details?id=com.idlegandalf.httprequestwidget&hl=en)
or [IFTTT](https://ifttt.com/) to open the door.

The api-keys have to be saved in a file named `apikeys.json` at the DoorPI
installation directory.

Example:
```JSON
{
  "f23c7114-f6b7-4269-a5a0-a58dcd671952": {
    "type": "master",
    "owner": "Gatekeeper (Can open the door at any moment)"
  },
  "0492af52-b10e-4be8-b378-f4986c10c1fa": {
    "type": "restricted",
    "owner": "Employee (Can open the door Mo-Fr 07:00-18:00)"
  },
  "25389c07-5902-4da5-a397-0c51b43f2846": {
    "type": "limited",
    "owner": "Guest (Can open the door Mo-Fr 07:00-18:00 within an given date range)",
    "from": "01.04.2019",
    "till": "01.05.2019"
  },
  "88e8fb43-c762-4aa6-a72c-d5a0ed333f66": {
    "type": "once",
    "owner": "Visitor (Can once-only open the door Mo-Fr 07:00-18:00 within an given date range)",
    "from": "01.03.2019",
    "till": "01.05.2019"
  }
}
```

When a valid api-key is given a JSON result `{"open": "{timestamp}"}` will be returned,
on invalid api-key `{'error': "Unauthorized"}` with HTTP status code 401. When a one-time
key (`"type": "once"`) was used, it is written with a timestamp into the file `usedkeys.json`
to ensure it isn't used any more.

```Bash
curl http://door.local:8080/api/open/f23c7114-f6b7-4269-a5a0-a58dcd671952
{"open": "1550962295.92"}
```

## Development

### Simulation Mode

If the requirement `RPi.GPIO` can't be fulfilled on the agent installation,
the agent will switch into an emulation mode and add a `simulate ring` handler
to the agents web user interface reachable at `https://door.local:8080/simulation`

### Templates

To customize the look-and-feel of your DoorPI installation change the 
files in the templates directory to your needs. The templates are 
rendered by [tornado.template](http://www.tornadoweb.org/en/stable/template.html#),
part of the [Tornado](http://www.tornadoweb.org/en/stable/index.html)
Framework.
