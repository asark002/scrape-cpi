import json
import socket
import structlog
from twisted.internet import reactor



class UDP(object):


    def __init__(self, addr, port):
        self.addr = addr
        self.port = port
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        reactor.addSystemEventTrigger('after', 'shutdown', self._close_sock)    #pylint: disable=no-member


    def __call__(self, _, __, event_dict):
        """
        Called from structlog
        """
        self.udp.sendto(
            json.dumps(event_dict).encode('utf8'),
            (self.addr, self.port))
        return event_dict


    def _close_sock(self):
        """
        Close UDP socket
        """
        self.udp.close()


def log_level(_, level, event_dict):
    """
    Place the log level in the dict
    """
    event_dict['log_level'] = level
    return event_dict


def setup(remote_log_addr, remote_log_port):
    """
    Setup universal logging
    """
    structlog.configure(
        processors = [ 
            log_level,
            structlog.processors.TimeStamper(),
            structlog.processors.JSONRenderer(),
            UDP(remote_log_addr, remote_log_port),
        ]
    )
