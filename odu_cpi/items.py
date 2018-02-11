# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class OduCpiItem(scrapy.Item):
    """
    Container for ODU CPI items
    """
    project_name = scrapy.Field()
    course = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
