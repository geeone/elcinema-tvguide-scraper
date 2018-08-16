# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ChannelItem(scrapy.Item):
    channelName = scrapy.Field()
    channelLogo = scrapy.Field()
    frequency = scrapy.Field()
    shows = scrapy.Field()


class RamadanItem(scrapy.Item):
    showName = scrapy.Field()
    showImage = scrapy.Field()
    showType = scrapy.Field()
    genre = scrapy.Field()
    description = scrapy.Field()
    cast = scrapy.Field()
    tvguide = scrapy.Field()
