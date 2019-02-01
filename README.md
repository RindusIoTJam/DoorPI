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

### agent
The agent sits near the bell with the door opening button and 
detects a ring, sends it to the server and eventually handles
a open-door event.

#### Installation

Connect to the rpi0w by ssh and change to a directory where
you want the agent to reside, e.g. inside /usr/local with
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

Now ...

### server

