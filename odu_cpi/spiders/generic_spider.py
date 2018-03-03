from os.path import splitext
import re

import scrapy
from scrapy.spidermiddlewares import httperror
import structlog
from twisted.internet import error as tx_error
from twisted.web import http    # provide universal tools for HTTP parsing

from odu_cpi import items, settings



class PreviousProjectSpider(scrapy.Spider):


    name = 'generic'
    download_timeout = 5.0
    _crawl_depth = 1
    _url_blacklist = [
        'www.cs.odu.edu',
        'www.cs.odu.edu/~cs410',
        'www.cs.odu.edu/~cs411',
        'web.odu.edu']
    _regex_domain_blacklist = re.compile(r'.*(facebook|linkedin|reddit|twitter)\.com')
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
        """
        """
        yield scrapy.Request(
            url = 'http://www.cs.odu.edu/~cpi/previous410-411.html',
            callback = self.parse_html,
            errback = self.errback)


    def parse_html(self, response):
        log = structlog.get_logger().bind(
            event = 'PARSE',
            module = __file__,
            source_url = response.url,
            content_type = 'HTML')

        crawl_depth = response.meta.get('crawl_depth', self._crawl_depth)

        body = response.xpath('//body')[0]
        title = response.xpath('//head//title/text()').extract_first()
        if title is None:
            title = response.url

        yield dict(
            source_url = response.url,
            title = title,
            content_type = 'HTML',
            content = body.extract())

        # add domain to set of traversed domains
        parsed_resp_url = http.urlparse(response.url.encode('utf')).decode()
        self._traversed_domains.add(parsed_resp_url.netloc)

        # extract links
        # @TODO use LxmlLinkExtractor
        hrefs = body.xpath('.//a/@href')
        for href in hrefs:
            href = href.extract()
            # check if href is absolute or relative
            try:
                if href[0] in ['.','/']:
                    href = ''.join([
                        parsed_resp_url.scheme,
                        parsed_resp_url.netloc.rstrip('/') + '/',
                        href[1:]
                    ])
                elif href[0] == '#':
                    # no need to self same site
                    continue
            except IndexError:
                # href = '' so no need to scrape
                continue

            parsed_href = http.urlparse(href.encode('utf8')).decode()

            # only parse HTTP links
            if parsed_href.scheme.upper() in ['HTTP', 'HTTPS']:
                # split the query string from the href, do not follow _href!
                _href = ''.join([
                    parsed_href.netloc,
                    parsed_href.path])

                # check if the domain is in the blacklist, skip if yes
                conditions_blacklist = any([
                    self._regex_domain_blacklist.match(parsed_href.netloc) is not None,
                    _href.rstrip('/') in self._url_blacklist])
                if conditions_blacklist:
                    # @TODO log
                    continue

                content_type = self.identify_type_from_url(_href)

                # make routing decision based on content type
                route = None
                if content_type in ['HTML']:
                    route = response.follow(
                        href,
                        callback = self.parse_html,
                        errback = self.errback,
                        meta = dict(crawl_depth = crawl_depth - 1))
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

