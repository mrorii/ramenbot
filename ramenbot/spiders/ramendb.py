#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy.http import Request
from scrapy.selector import Selector

from ramenbot.items import BusinessItem, ReviewItem, UserItem


def convert_to_float_if_float(s):
    try:
        return float(s)
    except ValueError:
        return s
    except TypeError:
        return s


def convert_to_int_if_int(s):
    try:
        return int(s)
    except ValueError:
        return s
    except TypeError:
        return s


def set_value_if_true(dictionary, key, value):
    if value:
        dictionary[key] = value


def trim(sentences):
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def extract_user_id(url):
    return int(re.findall(r'u/(\d+)', url)[0])


def extract_business_id(url):
    return int(re.findall(r's/(\d+)', url)[0])


BUSINESS_BASIC_INFO_FIELDS = [
    'business_hours',
    'holidays',
    'seats',
    'smoking',
    'nearest_station',
    'access',
    'parking',
    'open_date',
    'menu',
    'comments',
    'prizes',
    'tags',
    'external_links',
]


BUSINESS_BASIC_INFO_MAPPING = {
    u'営業時間': 'business_hours',
    u'定休日': 'holidays',
    u'席数': 'seats',
    u'喫煙': 'smoking',
    u'最寄り駅': 'nearest_station',
    u'アクセス': 'access',
    u'駐車場': 'parking',
    u'開店日': 'open_date',
    u'メニュー': 'menu',
    u'備考': 'comments',
    u'受賞歴': 'prizes',
    u'タグ': 'tags',
    u'外部リンク': 'external_links',
}


BUSINESS_METADATA_FIELDS = [
    'review_count',
    'review_user_count',
    'average_score',
    'ranking',
    'like_count',
]


BUSINESS_METADATA_MAPPING = {
    u'レビュー件数': 'review_count',
    u'レビューユーザー数': 'review_user_count',
    u'平均点': 'average_score',
    u'総合順位': 'ranking',
    u'スキ': 'like_count',
}


class RamenDbSpider(CrawlSpider):
    name = 'ramendb'
    allowed_domains = ['ramendb.supleks.jp']
    download_delay = 1.0

    start_urls = [
        'https://ramendb.supleks.jp/search?page=1',
    ]

    rules = [
        # Follow business pagination
        Rule(LxmlLinkExtractor(allow=(r'search\?page=\d+$')), follow=True),

        # Extract business
        # Example: https://ramendb.supleks.jp/s/282.html
        Rule(LxmlLinkExtractor(allow=(r's/\d+\.html$')),
             follow=True,
             callback='parse_business'),

        # Follow review pagination
        # Example: https://ramendb.supleks.jp/s/100962/review
        # Example: https://ramendb.supleks.jp/s/100962/review?page=2
        Rule(LxmlLinkExtractor(allow=(r'review(\?page=\d+)?$')), follow=True),

        # Extract review
        # Example: https://ramendb.supleks.jp/review/1057563.html
        Rule(LxmlLinkExtractor(allow=(r'review/\d+\.html$')),
             follow=True,
             callback='parse_review'),

        # Extract user
        # Example: https://ramendb.supleks.jp/u/141495.html
        Rule(LxmlLinkExtractor(allow=(r'u/\d+\.html$')),
             follow=True,
             callback='parse_user'),
    ]

    def is_ramendb(self, response):
        selector = Selector(response)
        return bool(selector.xpath("//div[@id='header-sites']"))

    def parse_business(self, response):
        def parse_basic_info(response):
            def extract_value(tr, field):
                if field == 'nearest_station':
                    return u''.join(tr.css('td div *::text').extract())
                elif field == 'menu' or field == 'comments':
                    return trim(tr.css('p.more *::text').extract())[:-1]
                elif field == 'tags':
                    return tr.css('a.tag::text').extract()
                elif field == 'external_links':
                    return [
                        {
                            'url': a.css('::attr(href)').extract_first(),
                            'name': a.css('span:not(.font-icon)::text')
                                     .extract_first(),
                        } for a in tr.css('a')
                    ]
                elif field == 'prizes':
                    return [
                        u''.join(trim(a.css('span *::text').extract()))
                        for a in tr.css('p.more > a.award')
                    ]
                else:
                    return tr.css('td::text').extract_first()

            basic_info = {}
            for tr in response.css('.datas tr'):
                key = tr.css('th::text').extract_first()
                if key not in BUSINESS_BASIC_INFO_MAPPING:
                    continue
                field = BUSINESS_BASIC_INFO_MAPPING[key]

                value = extract_value(tr, field)
                basic_info[field] = value
            return basic_info

        def parse_metadata(response):
            def extract_value(tr, field):
                if field == 'ranking':
                    value = tr.css('td::text').extract_first('')
                else:
                    value = tr.css('td > span::text').extract_first('')
                if not value:
                    return

                value = value.replace(',', '') \
                             .rstrip(u'件') \
                             .rstrip(u'人') \
                             .rstrip(u'点') \
                             .rstrip(u'位')

                if field == 'average_score':
                    return convert_to_float_if_float(value)
                else:
                    return convert_to_int_if_int(value)

            metadata = {}
            for tr in response.css('table.key-value tr'):
                key = tr.css('th::text').extract_first()
                if key not in BUSINESS_METADATA_MAPPING:
                    continue
                field = BUSINESS_METADATA_MAPPING[key]

                value = extract_value(tr, field)
                metadata[field] = value
            return metadata

        if not self.is_ramendb(response):
            return Request(url=response.url, dont_filter=True)

        business = BusinessItem()
        business['business_id'] = int(re.findall(r's/(\d+)\.html$', response.url)[0])
        business['has_moved'] = bool(response.css('.moved'))
        business['has_retired'] = bool(response.css('.retire'))
        business['has_without'] = bool(response.css('.without'))
        business['has_closed'] = bool(response.css('.closed'))
        business['name'] = response.css('.shopname::text').extract_first()
        business['branch'] = response.css('.branch::text').extract_first()
        business['alternate_name'] = response.css('span[itemprop=alternateName]::text') \
                                             .extract_first()
        business['points'] = convert_to_float_if_float(
            u''.join(response.css('span[itemprop=ratingValue] *::text')
                             .extract())
        )

        business['prefecture'] = response.css('.area > a[href*=state]::text').extract_first()
        business['city'] = response.css('.area > a[href*=city]::text').extract_first()
        business['address'] = u''.join(response.css('span[itemprop=address] *::text').extract())
        business['phone_number'] = response.css('td[itemprop=telephone]::text').extract_first()

        basic_info = parse_basic_info(response)
        for field in BUSINESS_BASIC_INFO_FIELDS:
            if field not in basic_info:
                continue
            business[field] = basic_info[field]

        metadata = parse_metadata(response)
        for field in BUSINESS_METADATA_FIELDS:
            if field not in metadata:
                continue
            business[field] = metadata[field]

        return business

    def parse_review(self, response):
        if not self.is_ramendb(response):
            return Request(url=response.url, dont_filter=True)

        def parse_noodle_and_soup(response):
            style = response.css('.style::text').extract_first()
            return style.lstrip('[').rstrip(']').split('/')

        def parse_comments(response):
            comments = []

            for comment in response.css('#comment .one'):
                comments.append({
                    'text': trim(comment.css('p::text').extract()),
                    'user_id': extract_user_id(comment.css('.foot > span > a::attr(href)')
                                                      .extract_first()),
                    'post_date': comment.css('.foot > span::text')
                                        .extract_first()
                                        .strip()
                                        .strip('|')
                                        .strip(),
                })
            return comments

        review = ReviewItem()
        review['review_id'] = int(re.findall(r'review/(\d+)\.html$', response.url)[0])
        review['item_name'] = response.css('span[itemprop=itemReviewed]::text').extract_first()
        review['noodle_type'], review['soup_type'] = parse_noodle_and_soup(response)
        review['score'] = convert_to_int_if_int(response.css('.score::text').extract_first())
        review['attention'] = response.css('.attention::text').extract_first()
        review['text'] = trim(response.css('span[itemprop=description]::text').extract())
        business_url = response.css('.props > span > a::attr(href)').extract_first()
        review['business_id'] = extract_business_id(business_url)
        user_url = response.css('.props > a::attr(href)').extract_first()
        review['user_id'] = extract_user_id(user_url)
        review['post_date'] = response.css('time::attr(datetime)').extract_first()
        review['comments'] = parse_comments(response)
        return review

    def parse_user(self, response):
        if not self.is_ramendb(response):
            return Request(url=response.url, dont_filter=True)

        user = UserItem()
        user['user_id'] = extract_user_id(response.url)
        user['name'] = response.css('.profile > h2::text').extract_first()
        user['properties'] = response.css('.profile > div.props::text').extract_first()
        user['description'] = response.css('.profile > p.comment::text').extract_first()

        metadata = response.css('.spct table.key-value td::text').extract()
        if len(metadata) == 2:
            user['average_score'] = convert_to_float_if_float(metadata[0].rstrip(u'点'))
            user['last_review_date'] = metadata[1].strip()

        metadata = [m.replace(',', '') for m in
                    response.css('.spct table.counts tr.value td *::text').extract()]
        if len(metadata) == 4:
            user['review_count'] = convert_to_int_if_int(metadata[0])
            user['review_business_count'] = convert_to_int_if_int(metadata[1])
            user['like_count'] = convert_to_int_if_int(metadata[2])
            user['iine_count'] = convert_to_int_if_int(metadata[3])

        return user
