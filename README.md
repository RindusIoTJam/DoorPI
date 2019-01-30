# DoorPI

## Abstract

## Components

### agent
The agent sits near the bell with the door opening button and 
detect a ring, sends it to the server and eventually handles a
open-door event.

#### Installation

##### Prerequisites

- Raspberry PI Zero W w/ Raspbian installed and remotely
  accessable

##### Setup

Connect to the rpi0w by ssh and change to a directory where
you want the agent to reside, e.g. inside /usr/local with
the name doorpi-agent

```
$ mkdir /usr/local/doorpi-agent
$ cd /usr/local/doorpi-agent
$ git clone git@github.com:RindusIoTJam/dooropener-Rpi0-.git .
$ virtualenv venv
$ source venv/bin/activate
$ cd agent
$ pip install -r requirements.txt
```

Now ...

### server
TODO