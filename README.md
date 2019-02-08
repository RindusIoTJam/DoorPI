# DoorPI

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
$ git clone https://github.com/RindusIoTJam/dooropener-Rpi0-.git .
$ virtualenv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

Now change the file `doorpi.json` to your needs and/or create a file
`local_settings.json` that has at least a unique `door.name` setting. 
See [Settings](/dooropener-Rpi0-#Settings) for more options.

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
| `gpio.ring`     | GPIO in-pin where the ring is detected. | `18` |
| `gpio.open`     | GPIO out-pin where the door-open relay connects. | `23` |
| `slack.webhook` | If set this webhook will be used to post a ring message to Slack | |
| `slack.channel` | Slack channel to post to. The default channel will be used if unset. | |
| `slack.baseurl` | BaseURL of DoorPI. Usually `http://door.acme.com:[webui.port]` | |
| `sentry.dsn` | For development purposes only. If it doesn't ring a bell, ignore this setting. ||

## Development

### Simulation Mode

If the requirement `RPi.GPIO` can't be fulfilled on the agent installation,
the agent will switch into an emulation mode and add a `simulate ring` 
button to the agents web user interface.

### Templates

To customize the look-and-feel of your DoorPI installation change the 
files in the templates directory to your needs. The templates are 
rendered by [tornado.template](http://www.tornadoweb.org/en/stable/template.html#),
part of the [Tornado](http://www.tornadoweb.org/en/stable/index.html)
Framework.