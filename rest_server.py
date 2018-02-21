"""

Environment variables:
===

* SCRAPY_SETTINGS_MODULE=odu_cpi.settings

"""

from scrapy.crawler import CrawlerRunner
import structlog
from klein import Klein

import _logging
from odu_cpi.spiders.previous_project_spider import PreviousProjectSpider



class RestServer(object):


    router = Klein()
    _active_crawl = False


    @router.route('/scrape', methods=['POST'])
    def scrape_content(self, request):
        """
        """
        if not self._active_crawl:
            # @TODO log
            self._active_crawl = True
            # @TODO set callback to set to False after certain interval

            runner = CrawlerRunner()
            deferred = runner.crawl(PreviousProjectSpider)
            # @TODO handle errors and reset flags
            deferred.addBoth(self._crawl_complete)
            deferred.addCallback(lambda x: 'CRAWL_COMPLETE')

            # @TODO return meaningful msg w/ reference #
            return 'CRAWL_INITIATED'

        # @TODO add response code and proper return msg
        request.setResponseCode(208)
        return 'CRAWL_IN_PROGRESS'


    def _crawl_complete(self, result):
        """
        """
        # @TODO log
        self._active_crawl = False



if __name__ == '__main__':
    # @TODO add cli args
    _logging.setup('127.0.0.1', 9000)
    app = RestServer()
    app.router.run(host='0.0.0.0', port=9801)
