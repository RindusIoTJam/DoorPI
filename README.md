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
The manager handles incoming ping and ring events.

#### Installation

Connect to the server by ssh and change to a directory where
you want the manager to reside, e.g. inside `/usr/local` with
the name doorpi-manager

```
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

The manager can be started  by `python manager.py`.

### Agent
The agent sits near the bell with the door opening button and 
detects a ring, sends it to the server and eventually handles
a open-door event.

#### Installation

Connect to the rpi0w by ssh and change to a directory where
you want the agent to reside, e.g. inside `/usr/local` with
the name doorpi-agent

```
$ mkdir /usr/local/doorpi-agent
$ cd /usr/local/doorpi-agent
$ git clone https://github.com/RindusIoTJam/dooropener-Rpi0-.git .
$ virtualenv venv
$ source venv/bin/activate
$ cd agent
$ pip install -r requirements.txt
```

Now change the file `doorpi.json` that it has a unique `DOOR_ID` 
and `API_KEY` and as well points to the manager istallation.

```
$ cat doorpi.json
{
  "DOOR_ID": "spain-malaga-cartama-elsexmo-ackermann-main",
  "DOOR_TO": "10",
  "API_URL": "http://127.0.0.1:8000",
  "API_KEY": "e12e0221-e016-4e4b-a3ea-3c12b51e335c"
}
```

The agent can be started  by `python doorpi.py` and offers a very
simple web interface at the configured `AGENT_HOST` and `AGENT_PORT`.
By default his is `http://0.0.0.0:8080`.

### Development

In the agent directory you can create a `local_settings.json` that
is ignored by `.gitignore` to overwrite agent setup. E.g.

```
$ cat local_setting.json
{
  "DOOR_ID": "spain-malaga-cartama-elsexmo-ackermann-main",
  "DOOR_TO": "10",
  "API_URL": "http://127.0.0.1:8000",
  "API_KEY": "e12e0221-e016-4e4b-a3ea-3c12b51e335c"
}
```

By this the agent is directly communicating to the local running
manager.