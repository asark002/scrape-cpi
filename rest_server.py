"""

Environment variables:
===

* SCRAPY_SETTINGS_MODULE=odu_cpi.settings

"""
from datetime import datetime
from functools import wraps
import json
from uuid import uuid4

from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
import structlog
from klein import Klein
import treq
from twisted.internet import defer

import _logging
from odu_cpi.spiders.generic_spider import GenericSpider



class Jsonify(object):


    def __init__(self, indent=0):
        self.indent = indent


    def __call__(self, fn):
        @wraps(fn)
        def _wrapper(*args, **kwargs):
            d = defer.maybeDeferred(fn, *args, **kwargs)
            d.addCallback(json.dumps, indent=self.indent)
            d.addErrback(self.jsonify_failure, args[1])
            d.addBoth(self.finalize, args[1])
            return d
        return _wrapper


    def jsonify_failure(self, failure, request):
        log = structlog.get_logger().bind(
            event = 'JSONIFY_ERROR',
            exception_repr = repr(failure.value),
            response_code = 500)
        log.error(error = 'JSON_SERVER_ERROR', message = 'Unable to convert response to JSON')
        request.setResponseCode(500)
        return json.dumps({'error': 'JSON_SERVER_ERROR'}, indent=self.indent)


    def finalize(self, result, request):
        request.responseHeaders.addRawHeader('Content-Type', 'application/json')
        return result



class RestServer(object):


    router = Klein()
    jsonify = Jsonify(indent=2)
    status_report = {}
    active_crawl = False


    @router.route('/crawl', methods=['POST'])
    @jsonify
    def crawl_for_content(self, request):
        """
        Initiate the crawl process.
        """
        # check if another crawl process is running
        if self.active_crawl:
            request.setResponseCode(208)
            return {'status': 'CRAWL_IN_PROGRESS'}

        # extract user input
        try:
            body = request.content.read().decode('utf8')
            user_input = json.loads(body)
            params = {}

            # crude type validation
            assert isinstance(user_input['source_urls'], list)
            assert isinstance(user_input['crawl_depth'], int)
            assert isinstance(user_input.get('elasticsearch_index', 'mariana.content'), str)

            url_whitelist = user_input.get('url_whitelist')
            assert isinstance(url_whitelist, (type(None), str, list))
            if url_whitelist is not None:
                params['_patterns_url_whitelist'] = url_whitelist

            url_blacklist = user_input.get('url_blacklist')
            assert isinstance(url_blacklist, (type(None), str, list))
            if url_blacklist is not None:
                params['_patterns_url_blacklist'] = url_blacklist

            domain_whitelist = user_input.get('domain_whitelist')
            assert isinstance(user_input.get('domain_whitelist'), (type(None), str, list))
            if domain_whitelist is not None:
                params['_patterns_domain_whitelist'] = domain_whitelist

            domain_blacklist = user_input.get('domain_blacklist')
            assert isinstance(user_input.get('domain_blacklist'), (type(None), str, list))
            if domain_blacklist is not None:
                params['_patterns_domain_blacklist'] = domain_blacklist
        except (AssertionError, KeyError) as error:
            error_log = structlog.get_logger().bind(
                event = 'JSON_VALIDATION_ERROR',
                exception_repr = repr(error))
            error_log.error(message = 'Invalid user input')
            request.setResponseCode(400)
            return {'error': 'JSON_VALIDATION_ERROR'}
        except Exception as error:
            error_log = structlog.get_logger().bind(
                event = 'JSON_DECODE_ERROR',
                exception_repr = repr(error))
            error_log.error(message = 'Unable to decode content into JSON')
            request.setResponseCode(400)
            return {'error': 'JSON_ERROR'}

        # @TODO log
        self.active_crawl = True
        # @TODO set callback to set to False after certain interval

        # update status report dict
        crawl_start_datetime = datetime.utcnow()
        crawl_id = uuid4().hex
        self.status_report[crawl_id] = 'IN_PROGRESS'

        # get crawl settings
        crawl_settings = get_project_settings()
        elasticsearch_index = user_input.get('elasticsearch_index', 'mariana.content')
        if elasticsearch_index != crawl_settings['ELASTICSEARCH_INDEX']:
            crawl_settings['ELASTICSEARCH_INDEX'] = elasticsearch_index

        # run crawler
        runner = CrawlerRunner(crawl_settings)
        deferred = runner.crawl(
            GenericSpider,
            _source_urls = user_input['source_urls'],
            _crawl_depth = user_input['crawl_depth'],
            # @FIXME using the datetime as an id is misleading
            _crawl_start_datetime = crawl_start_datetime,
            **params)

        deferred.addCallback(self.on_crawl_success, crawl_id)
        deferred.addErrback(self.on_crawl_failure, crawl_id)
        deferred.addBoth(self.on_crawl_complete)

        # @TODO return meaningful msg w/ reference #
        return {'crawl_id': crawl_id, 'status': 'CRAWL_INITIATED'}


    @router.route('/crawl/status', methods=['GET'])
    @jsonify
    @defer.inlineCallbacks
    def crawl_status(self, request):
        """
        Get the current status of crawl
        """
        response = {'message_type': 'CRAWL_STATUS_REPORT', 'status_report': self.status_report}
        if self.active_crawl:
            response['crawl_in_progress'] = True
        else:
            response['crawl_in_progress'] = False

        # check if Elasticsearch server is available
        for url in get_project_settings()['ELASTICSEARCH_SERVERS']:
            health_list = response.setdefault('elasticsearch_health_checks', [])
            health_check_item = {'message_type': 'ELASTICSEARCH_HEALTH_CHECK', 'hostname': url}

            try:
                result = yield treq.get(url, timeout=3)
                if result.code == 200:
                    health_check_item.update({'status': 'OK'})
                else:
                    error_log = structlog.get_logger().bind(
                        event = 'ELASTICSEARCH_SERVICE_DOWN',
                        elasticsearch_hostname = url)
                    error_log.error(message = 'Elasticsearch service is down')
                    health_check_item.update({'status': 'ERROR'})
            except Exception as error:
                error_log = structlog.get_logger().bind(
                    event = 'ELASTICSEARCH_SERVICE_DOWN',
                    elasticsearch_hostname = url)
                error_log.error(
                    message = 'Elasticsearch service is down',
                    exception_repr = repr(error))
                health_check_item['status'] = 'ERROR'

            health_list.append(health_check_item)

        return response


    @router.route('/crawl/status/<crawl_id>', methods=['GET'])
    @jsonify
    def status_by_id(self, request, crawl_id):
        """
        Get the status of a specific id
        """
        response = {
            'message_type': 'CRAWL_STATUS',
            'crawl_id': crawl_id}
        current_status = self.status_report.get(crawl_id)

        if current_status is not None:
            response['status'] = current_status
        else:
            request.setResponseCode(404)
            response['error'] = 'CRAWL_ID_NOT_FOUND'

        return response


    def on_crawl_failure(self, failure, crawl_id):
        """
        Catastrophic failure within spider
        """
        log = structlog.get_logger().bind(
            event = 'FAILURE_DURING_CRAWL',
            exception_repr = repr(failure.value),
            crawl_id = crawl_id)
        log.error(message = 'Catastrophic failure during crawl')
        self.status_report[crawl_id] = 'FAILED'


    def on_crawl_success(self, result, crawl_id):
        """
        Crawl is successful
        """
        log = structlog.get_logger().bind(
            event = 'SUCCESSFUL_CRAWL',
            crawl_id = crawl_id)
        log.info(message = 'Successful crawl')
        self.status_report[crawl_id] = 'COMPLETE'


    def on_crawl_complete(self, result):
        """
        Cleanup after crawl is complete
        """
        # @TODO log
        self.active_crawl = False



if __name__ == '__main__':
    # @TODO add cli args
    # setup universal logging
    _logging.setup(
        es_logger_url = get_project_settings()['ELASTICSEARCH_SERVERS'][0],
        es_logger_index = 'mariana.logger',
        es_logger_type = 'log_item')

    app = RestServer()
    app.router.run(host = '0.0.0.0', port = 9801)
