from os.path import splitext

import scrapy
from scrapy.spidermiddlewares import httperror
import structlog
from twisted.internet import error as tx_error
from twisted.web import http    # provide universal tools for HTTP parsing

from odu_cpi import items, settings



class PreviousProjectSpider(scrapy.Spider):


    name = 'cpi'
    download_timeout = 5.0
    _default_crawl_depth = 1
    _url_black_list = [
        'www.cs.odu.edu',
        'www.cs.odu.edu/~cs410',
        'www.cs.odu.edu/~cs411',
        'web.odu.edu']
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
        'svg': 'IMAGE'}
    _processable_ext = ['PDF', 'MS_WORD', 'LIBREOFFICE', 'POWERPOINT', 'EXCEL', 'CSV']


    def start_requests(self):
        """
        """
        yield scrapy.Request(
            url = 'http://www.cs.odu.edu/~cpi/previous410-411.html',
            callback = self.parse,
            errback = self.errback)


    def parse(self, response):
        """
        """
        crawl_depth = response.meta.get('crawl_depth', self._default_crawl_depth)
        content_type = response.meta.get('content_type', 'UNKNOWN')
        if crawl_depth == self._default_crawl_depth:
            content_type = 'HTML'   # 1st URL most likly is HTML

        log = structlog.get_logger().bind(
            source_url = response.url,
            content_type = content_type)

        if content_type == 'HTML':
            body = response.xpath('//body')[0]
            yield {
                'source_url': response.url,
                'content_type': content_type,
                'title': response.xpath('//head//title/text()').extract_first(),
                'content': body.extract()}

            #
            links = body.xpath('.//a/@href')
            for element in links:
                raw_link = element.extract()
                parsed_url = http.urlparse(raw_link.encode('utf8')).decode()
                base_link = ''.join([
                    parsed_url.hostname or '',
                    parsed_url.path or '/']
                    ).rstrip('/')
                content_type = self.determine_type(base_link)
                if crawl_depth > 0:
                    if base_link not in self._url_black_list:
                        log.info(
                            event = 'FOLLOW_HREF',
                            href = raw_link,
                            crawl_depth = crawl_depth)
                        yield response.follow(
                            raw_link,
                            callback = self.parse,
                            errback = self.errback,
                            meta = dict(
                                crawl_depth = crawl_depth - 1,
                                content_type = content_type,
                            ),
                        )
                    else:
                        log.info(error = 'CANNOT_PARSE_BLACKLISTED_URL')
                if crawl_depth <= 0:
                    # do not crawl past this domain layer
                    # @TODO pass visited domains in metadata
                    if parsed_url.hostname in [None]:
                        log.info(
                            event = 'FOLLOW_HREF',
                            href = raw_link,
                            crawl_depth = crawl_depth)
                        yield response.follow(
                            raw_link,
                            callback = self.parse,
                            errback = self.errback,
                            meta = dict(
                                crawl_depth = crawl_depth,
                                content_type = content_type,
                            ),
                        )
        elif content_type in self._processable_ext:
            # @TODO
            yield {
                'source_url': response.url,
                'content_type': content_type,
                'title': response.url,
                'content': None}
        elif content_type in ['IMAGE']:
            log.info(event = 'SKIP_CONTENT_TYPE')
        else:
            log.warn(
                response_code = response.status,
                error = 'UNABLE_TO_PARSE')


    def errback(self, failure):
        """
        """
        log = structlog.get_logger().bind(message = str(failure.value))

        if failure.check(tx_error.TimeoutError):
            request = failure.request
            log.error(
                error = 'REQUEST_TIMEOUT',
                source_url = request.url)
        elif failure.check(httperror.HttpError):
            response = failure.value.response
            log.error(
                error = 'HTTP_STATUS',
                response_code = response.status,
                source_url = response.url)
        else:
            # @TODO add default handler
            pass


    def determine_type(self, link):
        """
        """
        extension = splitext(link)[1].strip('.')
        if extension == '':
            return 'HTML'
        return self._file_type_map.get(extension, 'UNKNOWN')

