# -*- coding: utf-8 -*-

from datetime import datetime as dt
from datetime import timedelta
import datetime
import locale
import scrapy
import pandas as pd

from elcinema.items import ChannelItem


class filfan_spider(scrapy.Spider):
    name = "filfan_channels"
    url = "http://www.filfan.com/channel/index"

    custom_settings = {
        'MONGODB_COLLECTION': 'channels',
        'CLEAR_COLLECTION': False,
    }

    headers = {
        'Host': 'www.filfan.com',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Upgrade-Insecure-Requests': 1,
        'Connection': 'keep-alive'
    }

    def start_requests(self):
        yield scrapy.Request(url=self.url, headers=self.headers, callback=self.get_channels, dont_filter=True)

    def get_channels(self, response):
        tv_channels = response.selector.css(
            ".tv_channel").xpath("./@href").extract()
        tv_channels = [
            "https://www.filfan.com{}".format(tv_channel) for tv_channel in tv_channels]
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
        channel_name = response.selector.css(".atr_1").xpath(
            "./text()").extract_first()
        if channel_name:
            channel_name = channel_name.strip().encode("utf-8")
            channel_logo = response.selector.css(
                ".picview>img").xpath("./@src").extract_first().encode("utf-8")
            frequency_first = response.selector.xpath(
                ".//div[5]/div[3]/div[2]/div/p[3]/em/text()").extract_first().strip().encode("utf-8")
            if frequency_first:
                frequency = response.selector.xpath(
                    ".//div[5]/div[3]/div[2]/div/p[4]/em/text()").extract_first().strip().encode("utf-8")
                if frequency:
                    frequency = frequency_first + " " + frequency
                else:
                    frequency = frequency_first

            tvgrid = response.selector.css(".TVContent").xpath("./tr")

            # MAGIC METHOD
            date_field = None
            tv_program_list = []
            program_list = []
            for tr in tvgrid:
                if tr.xpath("./@class").extract_first():
                    if date_field:
                        tv_program_list.append([date_field, program_list])
                    date_field = tr.xpath(
                        "./th/text()").extract_first()
                    if date_field:
                        date_field = date_field.strip().encode('utf-8')
                else:
                    program_list.append(tr)

            shows_list = []
            for tv_program in tv_program_list:
                locale.setlocale(locale.LC_ALL, "ar_EG.UTF-8")
                now_year = str(dt.today().year)
                this_date = tv_program[0]
                this_date = this_date + " " + now_year
                tvdate = dt.strptime(this_date, "%d %B %Y")

                dailyShows_list = []
                for i in xrange(len(tv_program[1])):
                    show_image = tv_program[1][i].css(
                        ".TVLogo>a>img").xpath("./@src").extract_first()
                    show_title = tv_program[1][i].css(".TVname>a").xpath(
                        "./text()").extract_first().strip().encode("utf-8")
                    genre = tv_program[1][i].css(".tvrepeat").xpath(
                        "./text()").extract_first().strip().encode("utf-8")
                    start_time = tv_program[1][i].css(".TVtime").xpath(
                        "./text()").extract_first().strip()
                    start_time = dt.strptime(start_time, "%H:%M").time()
                    start_time = dt.combine(tvdate.date(), start_time)
                    try:
                        end_time = tv_program[1][i + 1].css(".TVtime").xpath(
                            "./text()").extract_first().strip()
                        end_time = dt.strptime(end_time, "%H:%M").time()
                        end_time = dt.combine(tvdate.date(), end_time)
                    except:
                        end_time = (start_time + timedelta(minutes=60))
                    duration = int((end_time - start_time).total_seconds() // 60)
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

        item["channelName"] = channel_name
        item["channelLogo"] = channel_logo
        item["frequency"] = frequency
        item["shows"] = shows_list
        yield item
