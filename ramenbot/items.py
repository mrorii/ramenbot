# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class ReviewItem(Item):
    review_id = Field()
    item_name = Field()
    is_delivery = Field()
    noodle_type = Field()
    soup_type = Field()
    score = Field()
    attention = Field()
    text = Field()

    business_id = Field()
    user_id = Field()
    post_date = Field()

    comments = Field()
    iine_count = Field()


class BusinessItem(Item):
    business_id = Field()
    has_moved = Field()    # 移転
    has_retired = Field()  # 閉店
    has_without = Field()  # 提供終了
    has_closed = Field()   # 休業中
    name = Field()
    branch = Field()
    alternate_name = Field()
    points = Field()
    prefecture = Field()
    city = Field()
    address = Field()
    phone_number = Field()
    business_hours = Field()
    holidays = Field()
    seats = Field()
    smoking = Field()
    nearest_station = Field()
    access = Field()
    parking = Field()
    open_date = Field()
    menu = Field()
    comments = Field()
    prizes = Field()
    tags = Field()
    external_links = Field()

    review_count = Field()
    review_user_count = Field()
    average_score = Field()
    ranking = Field()
    like_count = Field()


class UserItem(Item):
    user_id = Field()
    name = Field()
    properties = Field()
    description = Field()
    average_score = Field()
    last_review_date = Field()
    links = Field()

    review_count = Field()
    review_business_count = Field()
    like_count = Field()
    iine_count = Field()
