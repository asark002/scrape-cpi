import json
import socket
import structlog
from twisted.internet import reactor



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
        ]
    )
