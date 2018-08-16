# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymongo


class ElcinemaPipeline(object):
    def process_item(self, item, spider):
        return item


class MongoPipeline(object):
    '''
        Saves the scraped item to mongodb.
    '''

    mongo_collection = None

    def __init__(self, mongo_server, mongo_port, mongo_db):
        self.mongo_server = mongo_server
        self.mongo_port = mongo_port
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_server=crawler.settings.get('MONGODB_SERVER'),
            mongo_port=crawler.settings.get('MONGODB_PORT'),
            mongo_db=crawler.settings.get('MONGODB_DB'),
            # mongo_collection=crawler.settings.get('MONGODB_COLLECTION'),
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_server, self.mongo_port)
        self.db = self.client[self.mongo_db]
        self.mongo_collection = spider.settings.get('MONGODB_COLLECTION')
        clear_collection = spider.settings.get('CLEAR_COLLECTION')
        if clear_collection:
            self.db[self.mongo_collection].drop()

    def close_spider(self, spider):
        if self.mongo_collection == 'shows':
            self.db.youtube_shows.create_index(
                [("showName", pymongo.ASCENDING)], unique=True)
        self.client.close()

    def process_item(self, item, spider):
        self.db[self.mongo_collection].insert_one(dict(item))
        return item
