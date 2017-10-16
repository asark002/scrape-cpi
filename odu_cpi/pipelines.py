# -*- coding: utf-8 -*-

from os import path
import sqlite3

from scrapy.exceptions import DropItem

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


class WriteToFilePipeline(object):

    def process_item(self, item, spider):
        filename = '{0}-{1}.html'.format(item['course'], item['project_name'])
        with open(path.join('output', filename), 'w') as f:
            f.write(item['content'])
        return item


class SQLitePipeline(object):

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

