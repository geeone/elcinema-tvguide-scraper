# -*- coding: utf-8 -*-

from datetime import datetime as dt
from datetime import timedelta
import datetime
import locale
import scrapy
from pymongo import MongoClient
import pymongo
from elcinema import settings
import pandas as pd

from elcinema.items import RamadanItem


class elramadan_spider(scrapy.Spider):
    name = "elcinema_ramadan"
    url = "https://www.elcinema.com/ramadan/2017/?utf8=%E2%9C%93&order=views&country=&genre=&page={}"
    page = 1

    mongo_host = settings.MONGODB_SERVER
    mongo_port = settings.MONGODB_PORT
    mongo_db = settings.MONGODB_DB

    custom_settings = {
        'MONGODB_COLLECTION': 'shows',
        'CLEAR_COLLECTION': True,
    }

    headers = {
        'Host': 'www.elcinema.com',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Upgrade-Insecure-Requests': 1,
        'Connection': 'keep-alive'
    }

    def _connect_mongo(self, db, host='localhost', port=27017, username=None, password=None):
        """ A util for making a connection to mongo """
        if username and password:
            mongo_uri = 'mongodb://%s:%s@%s:%s/%s' % (
                username, password, host, port, db)
            conn = MongoClient(mongo_uri)
        else:
            conn = MongoClient(host, port)
        return conn[db]

    def start_requests(self):
        url = self.url.format(self.page)
        yield scrapy.Request(url=url, headers=self.headers, callback=self.get_pages, dont_filter=True)

    def get_pages(self, response):
        next_page = response.selector.xpath(
            ".//*[@class='pagination']/li")[-2].xpath("./@class").extract_first()
        shows = response.selector.css(
            ".thumbnail-wrapper>a").xpath("./@href").extract()
        shows = ["https://www.elcinema.com{}".format(show) for show in shows]
        for show in shows:
            yield scrapy.Request(url=show, headers=self.headers, callback=self.parse_show, dont_filter=True)
        if next_page == "arrow":
            self.page += 1
            url = self.url.format(self.page)
            yield scrapy.Request(url=url, headers=self.headers, callback=self.get_pages, dont_filter=True)
        else:
            try:
                df = pd.read_csv('to_add.csv')
                additional_shows = df[df.columns[0]].tolist()
                for add_show in additional_shows:
                    yield scrapy.Request(url=add_show, headers=self.headers, callback=self.parse_show, dont_filter=True)
            except:
                print 'file does not exist'

    def parse_show(self, response):
        try:
            item = RamadanItem()
            show_name = response.selector.xpath(
                ".//div[3]/div/div[4]/h1/span[1]/text()").extract_first()
            show_image = response.selector.xpath(
                ".//div[3]/div/div[5]/div/div[1]/a/img/@src").extract_first()
            show_type = response.selector.xpath(
                ".//div[3]/div/div[5]/div/div[2]/div[1]/div[2]/ul[1]/li[1]/text()").extract_first()
            genre = response.selector.xpath(
                ".//div[3]/div/div[5]/div/div[2]/div[1]/div[2]/ul[2]/li[2]/ul/li/a[1]/text()").extract_first()
            text_area = response.selector.xpath(
                ".//div[3]/div/div[5]/div/div[2]/p")
            description = text_area.xpath(
                "./text()").extract_first()
            description_plus = text_area.xpath("./span/text()").extract_first()
            if description_plus:
                description = description + description_plus
            cast_area = response.selector.css(
                ".intro-box .list-separator.list-title")

            cast = []
            for cast_row in cast_area:
                cast_values = cast_row.xpath("./li")
                cast_key = cast_values[0].xpath("./text()").extract_first()
                cast_body = cast_values[1:len(
                    cast_values) - 1].xpath("./a/text()").extract()
                cast_body = ', '.join(cast_body)
                cast.append(' '.join([cast_key, cast_body]))
            cast = '; '.join(cast)

            tvguide = []
            guide_table = response.selector.css(".expand").xpath("./tr")
            for i in xrange(len(guide_table)):
                locale.setlocale(locale.LC_ALL, "ar_EG.UTF-8")
                now_year = str(dt.today().year)
                this_date_list = guide_table[i].xpath(
                    "./td[2]/text()").extract_first().strip().encode("utf-8").split()[-2:]
                this_date = " ".join(this_date_list)
                this_date = this_date + " " + now_year
                show_date = dt.strptime(this_date, "%d %B %Y")

                locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
                start_time = guide_table[i].xpath("./td[3]/text()").extract_first().strip().encode(
                    "utf-8").replace("صباحًا", "AM").replace("مساءً", "PM")
                start_time = dt.strptime(start_time, "%I:%M %p").time()
                start_time = dt.combine(show_date.date(), start_time)
                try:
                    end_time = guide_table[i + 1].xpath("./td[3]/text()").extract_first().strip().encode(
                        "utf-8").replace("صباحًا", "AM").replace("مساءً", "PM")
                    end_time = dt.strptime(end_time, "%I:%M %p").time()
                    end_time = dt.end_time(show_date.date(), start_time)
                except:
                    end_time = (start_time + timedelta(minutes=60))
                duration = int((end_time - start_time).total_seconds() // 60)

                channel_name = guide_table[i].xpath(
                    "./td[1]/a[3]/text()").extract_first().strip().encode("utf-8")
                channel_logo = guide_table[i].xpath(
                    "./td[1]/a[2]/img/@src").extract_first().encode("utf-8")
                tvguide.append({"date": show_date.isoformat(),
                                "startTime": start_time.isoformat(),
                                "endTime": end_time.isoformat(),
                                "duration": duration,
                                "channel_name": channel_name,
                                "channel_logo": channel_logo})

            db = self._connect_mongo(db=self.mongo_db,
                                     host=self.mongo_host,
                                     port=self.mongo_port)
            try:
                db.youtube_shows.insert_one(
                    {'showName': show_name, 'YoutubeURL': None})
            except: pass

            item["showName"] = show_name
            item["showImage"] = show_image
            item["showType"] = show_type
            item["genre"] = genre
            item["description"] = description
            item["cast"] = cast
            item["tvguide"] = tvguide
            yield item
        except Exception as exc:
            print exc
            print response.url
