import json
import socket
import structlog

from scrapy.utils.project import get_project_settings
import treq



class ElasticsearchLogger(object):


    def __init__(self, es_url, es_index, es_type):
        self.es_url = es_url
        self.es_index = es_index
        self.es_type = es_type
        self.es_uri =  '/'.join([
            self.es_url,
            self.es_index,
            self.es_type])


    def __call__(self, _, level, event_dict):
        log_request = treq.post(
            self.es_uri,
            headers = {'content-type': 'application/json'},
            json = event_dict)
        log_request.addCallback(self.swallow_success)
        log_request.addErrback(self.swallow_error)
        return event_dict


    def swallow_success(self, response):
        """
        Swallow success callback
        """


    def swallow_error(self, failure):
        """
        Swallow errors
        """



def setup(es_logger_url, es_logger_index, es_logger_type):
    """
    Setup universal logging
    """
    structlog.configure(
        processors = [ 
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt='iso'),
            ElasticsearchLogger(es_logger_url, es_logger_index, es_logger_type),
            structlog.processors.JSONRenderer(),
        ]
    )
