# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from scrapy.exceptions import DropItem

from scrapy.item import Item
import pymongo

class ToutiaoPipeline(object):
    def process_item(self, item, spider):
        return item

#item去重以及去除无效项 
class DuplicatesPipeline(object):
    def __init__(self):
        self.title_set = set()

    def process_item(self, item, spider):
        title = item['title']
        if title in self.title_set:   #去除重复项
            raise DropItem("Duplicate title found: %s" % item)
        if title == None or title == "":    #去除空项
            raise DropItem("Invalid item found: %s" % item)
        self.title_set.add(title)
        return item

#将数据存入MongoDB
class MongoDBPipeline(object):
    @classmethod
    def from_crawler(cls, crawler):
        #从setting文件获取mongodb服务器以及数据库名，如果没有设置则使用默认项
        cls.DB_URI = crawler.settings.get('MONGO_DB_URI', '')
        cls.DB_NAME = crawler.settings.get('MONGO_DB_NAME', '')
        return cls()

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.DB_URI)
        self.db = self.client[self.DB_NAME]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        collection = self.db[spider.name]
        post = dict(item) if isinstance(item, Item) else item
        collection.insert_one(post)
        return item
