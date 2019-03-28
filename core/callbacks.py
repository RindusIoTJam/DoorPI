import abc


class Callback(object):
    """ Abstract Class to enforce implementation of ring_callback(secret_key, first_ring, follow_up) """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def timeout_callback(self, runtime: int) -> None:
        """
        Handle a timeout event

        :param runtime: time in seconds from first ring
        :type runtime: int
        """
        pass

    @abc.abstractmethod
    def open_callback(self, runtime: int) -> None:
        """
        Handle a open event

        :param runtime: time in seconds from first ring
        :type runtime: int
        """
        pass


