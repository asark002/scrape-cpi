"""

Environment variables:
===

* SCRAPY_SETTINGS_MODULE=odu_cpi.settings

"""

import json

from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
import structlog
from klein import Klein

import _logging
from odu_cpi.spiders.generic_spider import GenericSpider



class RestServer(object):


    router = Klein()
    _active_crawl = False


    @router.route('/crawl', methods=['POST'])
    def crawl_for_content(self, request):
        """
        Initiate the crawl process.
        """
        # check if another crawl process is running
        if self._active_crawl:
            # @TODO add response code and proper return msg
            request.setResponseCode(208)
            return 'CRAWL_IN_PROGRESS'

        # extract user input
        try:
            body = request.content.read().decode('utf8')
            user_input = json.loads(body)
            assert isinstance(user_input['source_urls'], list)
            assert isinstance(user_input['crawl_depth'], int)
        except:
            # @FIXME raise universal exception for JSON error
            request.setResponseCode(400)
            return 'JSON_ERROR'

        # @TODO log
        self._active_crawl = True
        # @TODO set callback to set to False after certain interval

        runner = CrawlerRunner(get_project_settings())
        deferred = runner.crawl(
            GenericSpider,
            _source_urls = user_input['source_urls'],
            _crawl_depth = user_input['crawl_depth'])
        # @TODO handle errors and reset flags
        deferred.addBoth(self._crawl_complete)
        deferred.addCallback(lambda x: 'CRAWL_COMPLETE')

        # @TODO return meaningful msg w/ reference #
        return 'CRAWL_INITIATED'


    @router.route('/crawl/status', methods=['GET'])
    def crawl_status(self, request):
        """
        Get the current status of crawl
        """
        if self._active_crawl:
            return 'CRAWL_IN_PROGRESS'
        return 'CRAWL_NOT_IN_PROGRESS'


    def _crawl_complete(self, result):
        """
        Cleanup after crawl is complete
        """
        # @TODO log
        self._active_crawl = False



if __name__ == '__main__':
    # @TODO add cli args
    # @TODO setup universal logging
    app = RestServer()
    app.router.run(host='0.0.0.0', port=9801)
