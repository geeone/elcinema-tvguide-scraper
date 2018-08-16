# -*- coding: utf-8 -*-

from datetime import datetime as dt
from datetime import timedelta
import datetime
import locale
import scrapy
import pandas as pd

from elcinema.items import ChannelItem


class elcinema_spider(scrapy.Spider):
    name = "elcinema_channels"
    url = "https://www.elcinema.com/ar/tvguide/"

    custom_settings = {
        'MONGODB_COLLECTION': 'channels',
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

    def start_requests(self):
        yield scrapy.Request(url=self.url, headers=self.headers, callback=self.get_channels, dont_filter=True)

    def get_channels(self, response):
        tv_channels = response.selector.xpath(
            ".//*[@id='tv-content']/div/div/div/div[1]/div/div[3]/a/@href").extract()
        tv_channels = [
            "https://www.elcinema.com{}".format(tv_channel) for tv_channel in tv_channels]
        try:
            df = pd.read_csv('to_skip.csv')
            to_skip_links = df[df.columns[0]].tolist()
            tv_channels = list(set(tv_channels)-set(to_skip_links))
        except:
            print 'file does not exist'

        for tv_channel in tv_channels:
            yield scrapy.Request(url=tv_channel, headers=self.headers, callback=self.parse_tvguide, dont_filter=True)

    def parse_tvguide(self, response):
        item = ChannelItem()
        channel_name = response.selector.css(".panel.jumbo>h1").xpath(
            "./text()").extract_first().strip().encode("utf-8")
        channel_logo = response.selector.css(
            ".columns.large-2>img").xpath("./@src").extract_first().encode("utf-8")
        frequency = response.selector.xpath(
            ".//div[3]/div/div[5]/div/div[2]/ul/li[3]/ul/li[2]/text()").extract_first().strip().encode("utf-8")

        tvgrid = response.selector.css(".row.tvgrid").xpath("./div")
        if len(tvgrid) % 2 != 0:
            raise Exception("tvgrid fatal error")

        shows_list = []
        locale.setlocale(locale.LC_ALL, "ar_EG.UTF-8")
        now_year = str(dt.today().year)
        for i in xrange(0, len(tvgrid), 2):
            this_date_list = tvgrid[i].xpath(
                "./div/text()").extract_first().strip().encode('utf-8').split()[-2:]
            this_date = " ".join(this_date_list)
            this_date = this_date + " " + now_year
            tvdate = dt.strptime(this_date, "%d %B %Y")

            dailyShows_list = []
            locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
            shows = tvgrid[i + 1].xpath("./div/div")
            for j in xrange(len(shows)):
                show_title = shows[j].xpath(
                    "./div[3]/ul/li[1]/a/text()").extract_first()
                if not show_title:
                    show_title = shows[j].xpath(
                        "./div[2]/ul/li[1]/text()").extract_first()
                if show_title:
                    show_title = show_title.encode("utf-8")
                    show_image = shows[j].xpath(
                        "./div[2]/a/img/@src").extract_first()
                    if show_image:
                        show_image = show_image.encode("utf-8")
                    genre = shows[j].xpath(
                        "./div[3]/ul/li[2]/text()").extract_first()
                    if genre:
                        genre = genre.strip().split()[0].encode("utf-8")
                    duration = shows[j].xpath(
                        "./div[1]/ul/li[2]/span/text()").extract_first()
                    if not duration:
                        duration = shows[j].xpath(
                            "./div[2]/ul/li[2]/span/text()").extract_first()
                    if duration:
                        duration = duration.strip()
                        duration = int(''.join(x for x in duration if x.isdigit()))
                    start_time = shows[j].xpath("./div[1]/ul/li[1]/text()").extract_first()
                    if not start_time:
                        start_time = shows[j].xpath("./div[2]/ul/li[2]/text()").extract_first()
                    if start_time:
                        start_time = start_time.strip().encode("utf-8").replace("صباحًا", "AM").replace("مساءً", "PM")
                        start_time = dt.strptime(start_time, "%I:%M %p").time()
                        start_time = dt.combine(tvdate.date(), start_time)
                    try:
                        end_time = shows[j + 1].xpath("./div[1]/ul/li[1]/text()").extract_first(
                        ).strip().encode("utf-8").replace("صباحًا", "AM").replace("مساءً", "PM")
                        end_time = dt.strptime(end_time, "%I:%M %p")
                        end_time = dt.combine(tvdate.date(), end_time)
                    except:
                        end_time = (start_time + timedelta(minutes=duration))
                    dailyShows = {"showName": show_title,
                                  "showImage": show_image,
                                  "genre": genre,
                                  "startTime": start_time.isoformat(),
                                  "endTime": end_time.isoformat(),
                                  "duration": duration}
                    dailyShows_list.append(dailyShows)
            showsList = {"date": tvdate.isoformat(),
                         "dailyShows": dailyShows_list}
            shows_list.append(showsList)
            locale.setlocale(locale.LC_ALL, "ar_EG.UTF-8")

        item["channelName"] = channel_name
        item["channelLogo"] = channel_logo
        item["frequency"] = frequency
        item["shows"] = shows_list
        yield item
