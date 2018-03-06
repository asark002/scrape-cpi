from copy import copy
from os.path import splitext
import re

from scrapy import Request, selector, Spider
from scrapy.spidermiddlewares import httperror
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
import structlog
from twisted.internet import error as tx_error
from twisted.web import http    # provide universal tools for HTTP parsing

from odu_cpi import items, settings



class GenericSpider(Spider):


    name = 'generic'
    _source_urls = []
    download_timeout = 10.0
    _crawl_depth = 1
    _patterns_url_whitelist = [
        r'.*cs\.odu\.edu/~(cpi|cs411|cs410)/?',
        r'.*(docs|sites)\.google.com/',
        ]
    _patterns_url_blacklist = [
        r'^.*\.cs\.odu\.edu/~(cpi|cs411|cs410)/?$',
        r'^.*\.cs\.odu\.edu/~cpi/previous410-411.html$',
        ]
    _patterns_domain_blacklist = [
        r'.*(accounts\.google|facebook|linkedin|reddit|twitter|youtube)']
    _link_extractor = LxmlLinkExtractor(
        allow = _patterns_url_whitelist,
        deny = _patterns_url_blacklist,
        deny_domains = _patterns_domain_blacklist,)
    _file_type_map = {
        'pdf': 'PDF',
        'doc': 'MS_WORD',
        'docx': 'MS_WORD',
        'odt': 'LIBREOFFICE',
        'pptx': 'POWERPOINT',
        'ppt': 'POWERPOINT',
        'xlsx': 'EXCEL',
        'xls': 'EXCEL',
        'csv': 'CSV',
        'php': 'HTML',
        'html': 'HTML',
        'htm': 'HTML',
        'org': 'HTML',
        'net': 'HTML',
        'com': 'HTML',
        'edu': 'HTML',
        'bmp': 'IMAGE',
        'gif': 'IMAGE',
        'jpeg': 'IMAGE',
        'jpg': 'IMAGE',
        'png': 'IMAGE',
        'svg': 'IMAGE',
        'xml': 'XML'}
    _processable_ext = [
        'EXCEL',
        'HTML',
        'LIBREOFFICE',
        'MS_WORD',
        'PDF',
        'POWERPOINT',
        'XML']
    _traversed_domains = set()


    def start_requests(self):
        for url in self._source_urls:
            yield Request(
                url = url,
                callback = self.parse,
                errback = self.errback,
                meta = {
                    'splash': {
                        'endpoint': 'render.json',
                        'args': {
                            'html': 1,
                            'iframes': 1,
                            'timeout': 10,
                        }
                    }
                }
            )


    def parse(self, response):
        """
        URL routing takes place here (for the most part)
        """
        # @TODO figure out how to due away with this upkeep
        # do not allow crawl_depth value to balloon to a high number
        if response.meta.get('crawl_depth', self._crawl_depth) < 0:
            response.meta['crawl_depth'] = 0

        # @TODO log
        if response.data.get('html'):
            # @FIXME is there a better way to yield from generator?
            route_generator = self.handle_html(
                response,
                selector.Selector(text=response.data['html']))
            for route in route_generator:
                yield route

        if len(response.data.get('childFrames', [])) > 0:
            frame_list = copy(response.data['childFrames'])
            while len(frame_list) > 0:
                frame_item = frame_list.pop()
                frame_html = frame_item.get('html', '')

                # @FIXME is there a better way to yield from generator?
                route_generator = self.handle_html(
                    response,
                    selector.Selector(text=frame_html))
                for route in route_generator:
                    yield route


    def handle_html(self, response, html_selector):
        """
        Parse HTML and extract links

        :type response: scrapy.http.Response
        :type html_selector: scrapy.selector.Selector
        :yields: dict, scrapy.Request
        """
        # @TODO handles for different parts of the HTML. eg. body, head, frameset
        log = structlog.get_logger().bind(
            event = 'PARSE_HTML',
            module = __file__,
            source_url = response.url,
            content_type = 'HTML')

        crawl_depth = response.meta.get('crawl_depth', self._crawl_depth)
        title = response.data.get('title', response.url)

        try:
            body = html_selector.xpath('//body')[0]
        except IndexError:
            body = selector.Selector(text='')

        yield dict(
            source_url = response.url,
            title = title,
            content_type = 'HTML',
            content = body.extract())

        # add domain to set of traversed domains
        parsed_resp_url = http.urlparse(response.url.encode('utf')).decode()
        self._traversed_domains.add(parsed_resp_url.netloc)

        # extract links
        href_list = self._link_extractor.extract_links(response)
        for link in href_list:
            # get the URL in string format
            href = link.url

           # separate meaningful pieces of URL
            try:
                parsed_href = http.urlparse(href.encode('utf8')).decode()
            except:
                # typically href URL is invalid
                log.error(error = "INVALID_URL", href=href)
                continue

            # only parse HTTP links
            if parsed_href.scheme.upper() in ['HTTP', 'HTTPS']:
                # split the query string from the href, do not follow _href!
                _href = ''.join([
                    parsed_href.netloc,
                    parsed_href.path])

                # determine file type from the URL
                content_type = self.identify_type_from_url(_href)

                # make routing decision based on content type
                route = None
                if content_type in ['HTML']:
                    route = response.follow(
                        href,
                        callback = self.parse,
                        errback = self.errback,
                        meta = dict(
                            crawl_depth = crawl_depth - 1,
                            splash = {
                                'endpoint': 'render.json',
                                'args': {
                                    'html': 1,
                                    'iframes': 1,
                                    'timeout': 10,
                                }
                            }
                        )
                    )
                elif content_type in self._processable_ext:
                    log.info('@TODO')     # @TODO

                # is crawl at 0 depth?
                conditions = any([
                    crawl_depth > 0,
                    all([
                        crawl_depth <= 0,
                        parsed_href.netloc in self._traversed_domains
                        ]),
                    ])
                if conditions and route is not None:
                    yield route


    def errback(self, failure):
        """
        Capture handled errors and exceptions when they occur.

        :type failure: twisted.python.failure.Failure
        """
        request = failure.request
        exception = failure.value
        log = structlog.get_logger().bind(
            event = 'EXCEPTION',
            exception_repr = repr(failure.value),
            source_url = request.url)

        if failure.check(tx_error.TimeoutError):
            log.error(error = 'REQUEST_TIMEOUT')
        elif failure.check(httperror.HttpError):
            response = failure.value.response
            log.error(
                error = 'NON_200_STATUS',
                response_code = response.status)
        else:
            log.error(error = 'GENERIC_ERROR')


    def identify_type_from_url(self, url):
        """
        :param url:
        :type url: str
        :return: File format in uppercase string. Default is "UNKNOWN".
        """
        extension = splitext(url)[1].strip('.').lower()
        if extension == '':
            return 'HTML'
        return self._file_type_map.get(extension, 'UNKNOWN')

