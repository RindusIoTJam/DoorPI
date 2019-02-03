# DoorPI

## Abstract

Use a RaspberryPi Zero W to detect a ring at a remote door bell
and open also the door remotely. 

##### Prerequisites

- RaspberryPi Zero W w/ Raspbian installed and remotely
  accessable with the to-be-build DoorPI-HAT connected
- Slack 'webhook access token' 
- git / python / pip / virtualenv installed on agent and server

## Agent

The agent sits near the bell with the door opening button and 
detects a ring, sends a message to slack and eventually handles
a open-door event.

### Installation

Connect to the rpi0w by ssh and change to a directory where
you want the agent to reside, e.g. inside `/usr/local` with
the name doorpi-agent

```Bash
$ mkdir /usr/local/doorpi-agent
$ cd /usr/local/doorpi-agent
$ git clone https://github.com/RindusIoTJam/dooropener-Rpi0-.git .
$ virtualenv venv
$ source venv/bin/activate
$ cd agent
$ pip install -r requirements.txt
```

Now create a file `local_settings.json` that has at least a unique
`DOOR_NAME`. See _Local Settings_ for more options.

```JSON
{
  "DOOR_NAME": "spain-malaga-cartama-elsexmo-ackermann-main",
}
```

The agent can be started  by `python doorpi.py` and offers a very
simple web interface at the configured `AGENT_HOST` and `AGENT_PORT`.
By default his is `http://0.0.0.0:8080`.

## Local Settings

In the agent and manager directory you can create a `local_settings.json`
that is ignored by `.gitignore` to overwrite setup. E.g.

```JSON
{
  "DOOR_NAME": "spain-malaga-pta-habitec-rindus-main",
}
```

### Agent

| JSON key        | Description |Default |
| --------------- | ----------- | ------ |
| `AGENT_HOST`    | Listen address of the agents web interface. Set to `0.0.0.0` to listen on all available addresses. | `127.0.0.1` |
| `AGENT_PORT`    | Listen port of the agents web interface. | `8080` |
| `DOOR_NAME`     | An identifier of this door agent. | `your-mother` |
| `OPEN_TIMEOUT`  | Timeout accept an open response on a ring event. | `60` |
| `GPIO_RING`     | GPIO in-pin where the ring is detected. | `18` |
| `GPIO_OPEN`     | GPIO out-pin the the door-open relay connects. | `23` |
| `SLACK_WEBHOOK` | If set this webhook will be used to post a ring message to Slack | |
| `SLACK_CHANNEL` | Slack channel to post to. The default channel will be used if unset. | |

## Development

If the requirement `RPi.GPIO` can't be fulfilled on the agent installation,
the agent will switch into an emulation mode and add a `simulate ring` 
button to the agents web user interface.