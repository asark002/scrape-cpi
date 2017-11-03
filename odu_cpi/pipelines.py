# -*- coding: utf-8 -*-

from io import StringIO
from os import mkdir, path
import sqlite3

from scrapy.exceptions import DropItem
import six

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


class WriteToFilePipeline(object):
    """
    Write the body of the scraped project site into a local HTML file
    """

    def process_item(self, item, spider):
        # make output folder if not present
        # @TODO make dir name configurable in settings
        if not path.exists('output'):
            mkdir('output')

        # create a HTML file using body of project site
        filename = '{0}-{1}.html'.format(item['course'], item['project_name'])
        with open(path.join('output', filename), 'w') as f:
            f.write(item['content'])

        return item


class SQLitePipeline(object):
    """
    Write the body of the scraped project site into a SQLite database.
    """

    def open_spider(self, spider):
        self.db = sqlite3.connect('test.sqlite')

    def close_spider(self, spider):
        self.db.close()

    def process_item(self, item, spider):
        cur = self.db.cursor()
        stmt = """SELECT url FROM content WHERE url=?"""
        cur.execute(stmt, (item['url'],))
        query = cur.fetchall()
        if len(query) == 0:
            stmt = """
            INSERT INTO content
            (url, project_name, course, content)
            VALUES (?, ?, ?, ?)
            """
            cur.execute(stmt, (item['url'], item['project_name'], item['course'], item['content']))
            self.db.commit()
            return item
        cur.close()
        return DropItem('%s already stored' % (item['url']))


class ParseElements(object):

    ignored_tags = ['script']

    def process_item(self, item, spider):
        iobuffer = StringIO()
        self._parse(item['content'], iobuffer)
        #print(iobuffer.getvalue())

    def _parse(self, element, iobuffer):
        """
        """
        for elem in element:
            if elem.tag not in self.ignored_tags:
                #self.buff.write(elem.text)
                if isinstance(elem.text, six.string_types):
                    iobuffer.write(elem.text)
            self._parse(elem, iobuffer)

