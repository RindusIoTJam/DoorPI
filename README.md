# DoorPI

## Abstract

Use a RaspberryPi Zero W to detect a ring at a remote door bell
and open also the door remotely. 

##### Prerequisites

- RaspberryPi Zero W w/ Raspbian installed and remotely
  accessable with the to-be-build DoorPI-HAT connected
- Server where the API component can sit and hide behind
  a HTTPS terminating server like Apache2 or NGINX.
- Slack 'bot user oauth access token' 
- git / python / pip / virtualenv installed on agent and server

## Components

### Server
The manager handles incoming ping, ring and open events.

#### Installation

Connect to the server by ssh and change to a directory where
you want the manager to reside, e.g. inside `/usr/local` with
the name doorpi-manager

```Bash
$ mkdir /usr/local/doorpi-manager
$ cd /usr/local/doorpi-manager
$ git clone https://github.com/RindusIoTJam/dooropener-Rpi0-.git .
$ virtualenv venv
$ source venv/bin/activate
$ cd manager
$ pip install -r requirements.txt
```

Setup the http listening host/port for incoming requests as well
as the doors this manager is supposed to handle. It is highly
recommended to run the manager behind a Apache or NGINX that
terminate incoming requests by https and forward them to the
manager.

When a `BOT_TKN` (See _Local Settings_) for an agent is given,
the manager spawns a bot that connects to the given Slack workspace
and announces ring evens wherever the bot is invited into a channel.

The manager can be started  by `python manager.py`.

### Agent
The agent sits near the bell with the door opening button and 
detects a ring, sends it to the server and eventually handles
a open-door event.

#### Installation

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
`DOOR_ID` and `API_KEY` and as well points to the manager installation
(`API_URL`). See _Local Settings_ for more options.

```JSON
{
  "DOOR_ID": "spain-malaga-cartama-elsexmo-ackermann-main",
  "API_URL": "http://127.0.0.1:8000",
  "API_KEY": "e12e0221-e016-4e4b-a3ea-3c12b51e335c"
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
  "DOOR_ID": "spain-malaga-pta-habitec-rindus-main",
  "API_URL": "https://iot.rindus.de/services/smart-portero",
  "API_KEY": "e12e0221-e016-4f4b-a3ea-3c12b51e335c"
}
```

### Agent

| JSON key | Description |Default |
| -------- | ------- | ------ |
| `AGENT_HOST` | The listen address of the agents web interface. Set to `0.0.0.0` to listen on all available addresses. | `127.0.0.1` |
| `AGENT_PORT` | The listen port of the agents web interface. | `8080` |
| `DOOR_ID`    | An identifier of this door agent. | `your-mother` |
| `DOOR_TO`    | Timeout to wait for an open response on a ring event. | `60` |
| `GPIO_RING`  | GPIO in-pin where the ring is detected. | `18` |
| `GPIO_OPEN`  | GPIO out-pin the the door-open relay connects. | `23` |
| `API_URL`    | The URL of the manager installation. | `https://example.net/service/doorpi` |
| `API_KEY`    | The API-Key to send with the events. | `fat-ugly` |

### Manager

| JSON key | Description |Default |
| -------- | ------- | ------ |
| `MANAGER_HOST` | The listen address of the managers API interface. Set to `0.0.0.0` to listen on all available addresses. | `127.0.0.1` |
| `MANAGER_PORT` | The listen port of the managers API interface. | `8000` |
| `DOORS` | A list of door installations to be handled. | Example `your-mother` door. |
| `DOORS`.`door-id` | An identifier of an door agent. | |
| `DOORS`.`door-id`.`API_KEY` | A API-Key the door has to send to be authenticated. | |
| `DOORS`.`door-id`.`BOT_TKN` | The SlackBot token to use for the bot. | |

## Development

If the requirement `RPi.GPIO` can't be fulfilled on the agent installation,
the agent will switch into an emulation mode and add a `simulate ring` 
button to the agents web user interface.