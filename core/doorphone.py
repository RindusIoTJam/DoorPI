import logging
import time
import threading
import uuid
import asyncio

try:
    from .callbacks import Callback
except ModuleNotFoundError:
    from callbacks import Callback

SIMULATION = False


try:
    from gpiozero import Button, DigitalOutputDevice
except ImportError:
    logging.warning("DOORPHONE RUNNING IN SIMULATION MODE")
    SIMULATION = True


class DoorPhone(object):
    """
    DoorPhone Thread Safe Singleton
    """
    _instance = None
    _door_open_thread = None
    _lock = threading.Lock()
    last_open = time.time()

    DEFAULT_TIMEOUT = 60

    def __new__(cls, callback: Callback, gpio_ring=24, gpio_open=23):
        """
        Create DoorPhone Instance

        All GPIO pin numbers use Broadcom (BCM) numbering by default.
        See: https://gpiozero.readthedocs.io/en/stable/recipes.html#pin-numbering

        :param callback: Instance implementing Callback()'s abstract methods
        :param gpio_ring: GPIO pin number where a ring is detected by a pull-down signal
        :param gpio_open: GPIO pin number where a open is fired by a pull-up signal
        :type callback: CallBack
        :type gpio_ring: int
        :type gpio_open: int
        """
        if DoorPhone._instance is None:
            with DoorPhone._lock:
                if DoorPhone._instance is None:
                    try:
                        DoorPhone._instance = super(DoorPhone, cls).__new__(cls)
                        DoorPhone._instance.secret_key = None
                        DoorPhone._instance.timeout = DoorPhone.DEFAULT_TIMEOUT
                        DoorPhone._instance.timeout_thread = None
                        DoorPhone._instance.callback = callback
                        DoorPhone._instance.gpio_ring = gpio_ring
                        DoorPhone._instance.gpio_open = gpio_open
                        DoorPhone._instance.open_dev = DigitalOutputDevice(gpio_open)
                        DoorPhone._instance.ring_dev = Button(gpio_ring, hold_time=0.25)
                    except NameError:
                        # RUNNING IN SIMULATION MODE
                        DoorPhone._instance.open_dev = None
                        DoorPhone._instance.ring_dev = None
                        pass
        return DoorPhone._instance

    @classmethod
    def instance(cls):
        """
        Return a DoorPhone instance

        :return: instance of DoorPhone
        :rtype: DoorPhone
        """
        if DoorPhone._instance is None:
            raise RuntimeError("DoorPhone not initialized.")
        else:
            return DoorPhone._instance

    def __str__(self) -> str:
        """ x.__str__() <==> str(x) """
        return "%s (gpio_ring=%s, gpio_open=%s, ring_callback=%s)" % (self.__repr__(),
                                                                      self.gpio_ring,
                                                                      self.gpio_open,
                                                                      self.callback)

    def __init__(self, **kwargs) -> None:
        """
        Initialize DoorPhone Instance

        :param kwargs: parameters coming from __new__(...)
        """
        if not isinstance(self.callback, Callback):
            raise RuntimeError("callback is not of type Callback: %s" % self.callback)

        self.timeout = self.timeout
        self.timeout_thread = self.timeout_thread
        self.callback = self.callback
        try:
            self.ring_dev.when_pressed = self.__ring_callback__
        except AttributeError:
            # RUNNING IN SIMULATION MODE
            logging.debug("Initialized DoorPhone with kwargs: %s" % kwargs)

    def __ring_callback__(self, device: object) -> None:
        """
        Callback wrapper for self.ring_dev.when_pressed

        :param device: The "device" that triggered the callback execution
        :type device: object
        """
        timestamp = time.time()

        # prevent open firing new ring
        if timestamp - DoorPhone.last_open > 2:
            with DoorPhone._lock:
                logging.debug("Got ring from %s" % device)
                if self.timeout_thread is None:
                    self.first_ring = timestamp
                    # First ring, create a secret key
                    self.secret_key = str(uuid.uuid4())
                    self.timeout_thread = TimeoutThread(door_phone=self,
                                                        callback=self.callback,
                                                        timeout=self.timeout)
                    self.timeout_thread.start()
                    self.callback.ring_callback(secret_key=self.secret_key,
                                                first_ring=True,
                                                follow_up=False)
                else:
                    # Follow-up ring: reuse existing secret
                    self.timeout_thread.extend()
                    self.callback.ring_callback(secret_key=self.secret_key,
                                                first_ring=False,
                                                follow_up=True)
        else:
            logging.info("Ignoring RING b/c within 5 seconds after last OPEN")

    def simulate_ring(self) -> None:
        """ Inject a RING into the system """
        self.__ring_callback__("SimulationDevice")

    def set_timeout_callback(self, callback: Callback, timeout=DEFAULT_TIMEOUT) -> None:
        """
        Set the Instance implementing Callback.timeout_callback() to be called when timeout occurs.

        :param callback: Instance implementing TimeoutCallback.timeout_callback()
        :param timeout: Timeout in seconds till TimeoutCallback.timeout_callback() is called
        :type callback: Callback
        :type timeout: int
        """
        self.timeout = timeout
        self.callback = callback

    def open_door(self, secret_key: str) -> bool:
        """
        Open the door with the secret key

        :param secret_key: The secret key
        :type secret_key: str
        :return: True if door was opened, False otherwise
        :rtype: bool
        """

        if self.timeout_thread is not None and self.secret_key == secret_key:
            # Stop and remove TimeoutThread so no more opens are accepted
            self.timeout_thread.stop()
            self.timeout_thread = None
            logging.debug("Accepting open request")
            return self._open_door()

        logging.warning("Ignoring open request without prior ring and/or wrong key")
        return False

    def _api_open_door(self) -> bool:
        """
        Opens the door without the secret key or a ring

        :return: Always True at the moment
        :rtype: bool
        """
        DoorPhone.last_open = time.time()
        if DoorPhone._door_open_thread is None:
            DoorPhone.door_open_thread = DoorOpenThread(self.open_dev)
            DoorPhone.door_open_thread.start()

        return True

    def _open_door(self) -> bool:
        """
        Opens the door without the secret key but expecting a ring

        :return: Always True at the moment
        :rtype: bool
        """
        timestamp = time.time()
        DoorPhone.last_open = timestamp
        self.callback.open_callback(round(timestamp-self.first_ring))
        if DoorPhone._door_open_thread is None:
            DoorPhone.door_open_thread = DoorOpenThread(self.open_dev)
            DoorPhone.door_open_thread.start()

        return True


class DoorOpenThread(threading.Thread):
    """ DoorOpen Thread """
    _lock = threading.Lock()

    def __init__(self, open_device, open_seconds=1) -> None:
        """
        DoorOpen Thread initialisation

        :param open_device: DigitalOutputDevice to use
        :param open_seconds: Seconds to trigger open_device high before going into low state
        :type open_device: DigitalOutputDevice
        :type open_seconds: int
        """
        self.open_seconds = open_seconds
        self.open_device = open_device
        super(DoorOpenThread, self).__init__()

    def run(self) -> None:
        """ Flip open_device low-> for a given time """

        # see https://github.com/tornadoweb/tornado/issues/2308
        # and https://github.com/tornadoweb/tornado/issues/2352
        asyncio.set_event_loop(asyncio.new_event_loop())

        with DoorOpenThread._lock:
            logging.debug("DoorOpenThread started")
            try:
                self.open_device.on()
                time.sleep(self.open_seconds)
                self.open_device.off()
            except AttributeError:
                time.sleep(self.open_seconds)
                pass
            logging.info("DoorOpenThread finished opening the door")


class TimeoutThread(threading.Thread):
    """ Timeout Thread """

    def __init__(self, door_phone: DoorPhone, callback: Callback, timeout=60) -> None:
        """
        Timeout Thread initialisation

        :param door_phone: DoorPhone instance to inform on timeout
        :param callback: Instance implementing timeout_callback()
        :param timeout: Timeout in seconds
        :type door_phone: DoorPhone
        :type callback: Callback
        :type timeout: int
        """
        self.door_phone = door_phone
        if not isinstance(callback, Callback):
            raise RuntimeError("timeout_callback is not callable")

        self.callback = callback
        threading.Thread.__init__(self)
        self.timeout = timeout
        self.finish = round(time.time())+timeout
        self.wait = True

    def run(self) -> None:
        """ Wait for timeout to occur and stop """

        # see https://github.com/tornadoweb/tornado/issues/2308
        # and https://github.com/tornadoweb/tornado/issues/2352
        asyncio.set_event_loop(asyncio.new_event_loop())

        start_time = time.time()
        while self.wait and round(time.time()) < self.finish:
            logging.debug("remaining time to timeout: %s seconds" % (self.finish - round(time.time())))
            time.sleep(1)
        if self.wait:
            self.door_phone.timeout_thread = None
            self.callback.timeout_callback(round(time.time()-start_time))

    def extend(self) -> None:
        """ Extends the timeout to now + timeout """
        self.finish = round(time.time())+self.timeout

    def stop(self) -> None:
        """ Stop thread wating for timeout """
        self.wait = False


class __TestHandler(Callback):
    """ Helper Class for Callback Test """

    false_key = False
    double_open = False

    def open_callback(self, runtime: int) -> None:
        logging.info("OPENCALLBACK: runtime=%s" % runtime)

    def timeout_callback(self, runtime: int) -> None:
        """
        Handle a timeout event

        :param runtime: time in seconds from first ring
        :type runtime: int
        """
        logging.info("TIMEOUTCALLBACK: runtime=%s" % runtime)

    def ring_callback(self, secret_key: str, first_ring: bool, follow_up: bool) -> None:
        """
        Handle a ring event

        :param secret_key: The key to open
        :param first_ring: True if first ring
        :param follow_up: True if follow-up ring within timeout
        :type secret_key: str
        :type first_ring: bool
        :type follow_up: bool
        """
        logging.info("RINGCALLBACK: secret_key=%s, first_ring=%s, follow_up=%s" % (secret_key, first_ring, follow_up))
        if follow_up:
            if self.false_key:
                time.sleep(1)
                DoorPhone.instance().open_door("-")
            else:
                time.sleep(1)
                DoorPhone.instance().open_door(secret_key)

            if self.double_open:
                if self.false_key:
                    time.sleep(0.5)
                    DoorPhone.instance().open_door("-")
                else:
                    time.sleep(0.5)
                    DoorPhone.instance().open_door(secret_key)

    @classmethod
    def set_false_key(cls, false_key: bool):
        """
        Helper method

        :param false_key: Set True to use a false/failing key (default=False)
        :type false_key: bool
        """
        cls.false_key = false_key

    @classmethod
    def set_double_open(cls, double_open: bool):
        """
        Helper method

        :param double_open: Set True to request a second open (default=False)
        :type double_open: bool
        """
        cls.double_open = double_open


if __name__ == "__main__":
    """ Some Tests"""
    th = __TestHandler()

    DoorPhone.DEFAULT_TIMEOUT = 4

    x = DoorPhone(callback=th)
    y = DoorPhone.instance()

    if x is not y:
        raise AssertionError("DoorPhone is not a singleton!")
    logging.warning("TIMEOUT=2//TIMEOUT; RING -(Sleep:3)-> ... TIMEOUT")
    x.set_timeout_callback(callback=th, timeout=2)
    y.simulate_ring()

    if DoorPhone.instance().timeout_thread is None:
        raise AssertionError("timeout_thread doesn't exist while in timeout!")

    time.sleep(3)

    if DoorPhone.instance().timeout_thread is not None:
        raise AssertionError("DoorPhone.timeout_thread exist after timeout! %s" % DoorPhone.instance().timeout_thread)

    logging.warning("TIMEOUT=2//OPEN; RING -(Sleep:1)-> RING/OPEN-> ... OPEN")
    z = DoorPhone.instance()
    x.simulate_ring()
    time.sleep(1)
    y.simulate_ring()
    time.sleep(1)

    logging.warning("TIMEOUT=2//DENY_OPEN; RING -(Sleep:1)-> RING...OPEN -(Sleep:3)-> ... DENY_OPEN")
    __TestHandler.set_false_key(True)
    x.simulate_ring()
    time.sleep(1)
    y.simulate_ring()
    time.sleep(1)

    logging.warning("TIMEOUT=3//OPEN+DENY_OPEN; RING/OPEN/OPEN-> ... OPEN+DENY_OPEN")
    __TestHandler.set_false_key(False)
    __TestHandler.set_double_open(True)

    x.simulate_ring()
    time.sleep(1)
    y.simulate_ring()
    time.sleep(2)

    if DoorPhone.instance().timeout_thread is not None:
        raise AssertionError("timeout_thread exist after timeout! %s")
