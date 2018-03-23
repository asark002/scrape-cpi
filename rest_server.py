"""

Environment variables:
===

* SCRAPY_SETTINGS_MODULE=odu_cpi.settings

"""
from functools import wraps
import json
from uuid import uuid4

from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
import structlog
from klein import Klein

import _logging
from odu_cpi.spiders.generic_spider import GenericSpider



def jsonify(indent=0):
    def wrapper(fn):
        @wraps(fn)
        def _wrapper(*args, **kwargs):
            return json.dumps(fn(*args, **kwargs), indent=indent)
        return _wrapper
    return wrapper



class RestServer(object):


    router = Klein()
    status_report = {}
    active_crawl = False


    @router.route('/crawl', methods=['POST'])
    @jsonify(indent=2)
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
            assert isinstance(user_input['source_urls'], list)
            assert isinstance(user_input['crawl_depth'], int)
            assert isinstance(user_input.get('url_whitelist'), (type(None), str, list))
        except:
            # @FIXME raise universal exception for JSON error
            request.setResponseCode(400)
            return {'error': 'JSON_ERROR'}

        # @TODO log
        self.active_crawl = True
        # @TODO set callback to set to False after certain interval

        # update status report dict
        crawl_id = uuid4().hex
        self.status_report[crawl_id] = 'IN_PROGRESS'

        runner = CrawlerRunner(get_project_settings())
        deferred = runner.crawl(
            GenericSpider,
            _source_urls = user_input['source_urls'],
            _crawl_depth = user_input['crawl_depth'])
        # @TODO handle errors and reset flags
        deferred.addBoth(self._crawl_complete, crawl_id)

        # @TODO return meaningful msg w/ reference #
        return {'crawl_id': crawl_id, 'status': 'CRAWL_INITIATED'}


    @router.route('/crawl/status', methods=['GET'])
    @jsonify(indent=2)
    def crawl_status(self, request):
        """
        Get the current status of crawl
        """
        # @TODO set correct status code
        if self.active_crawl:
            return {'crawl_in_progress': True, 'status_report': self.status_report}
        return {'crawl_in_progress': False, 'status_report': self.status_report}


    @router.route('/crawl/status/<crawl_id>', methods=['GET'])
    @jsonify(indent=2)
    def status_by_id(self, request, crawl_id):
        """
        Get the status of a specific id
        """
        return {'status': self.status_report.get(crawl_id), 'crawl_id': crawl_id}


    def _crawl_complete(self, result, crawl_id):
        """
        Cleanup after crawl is complete
        """
        # @TODO log
        self.active_crawl = False
        self.status_report[crawl_id] = 'COMPLETE'



if __name__ == '__main__':
    # @TODO add cli args
    # @TODO setup universal logging
    app = RestServer()
    app.router.run(host='0.0.0.0', port=9801)
