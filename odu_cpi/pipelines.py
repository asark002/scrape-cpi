# -*- coding: utf-8 -*-

from scrapy.exceptions import DropItem
import structlog
from w3lib import html



class HandleContentType(object):


    # pylint: disable=unused-argument,no-self-use
    def process_item(self, item, spider):
        """
        """
        content_type = item.get('content_type', 'UNKNOWN')
        log = structlog.get_logger().bind(content_type = content_type)

        if content_type == 'HTML':
            plain_content = html.replace_escape_chars(
                html.remove_tags(item['content']),
                which_ones = ('\n','\t','\r','   '),
                replace_by = '')
            item['content'] = plain_content
        # @TODO
        elif content_type in ['PDF','MS_WORD', 'LIBREOFFICE', 'POWERPOINT', 'CSV', 'XLSX', 'XLS']:
            log.info(
                event = 'QUEUE_CONTENT',
                message = 'Pushing content for deferred processing')
        elif content_type in [None, 'UNKNOWN']:
            log.warn(error = 'UNRECOGNIZED_CONTENT_TYPE')

        return item
