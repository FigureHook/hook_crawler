import re
from datetime import date

import pytest
import requests as rq
from figure_parser.product import Product
from hook_crawlers.product_crawler.spiders import (AlterProductSpider,
                                                   GSCProductSpider)
from scrapy.http import HtmlResponse


class TestYearValidation:
    def test_begin_is_end(self):
        year = 2021
        spider = GSCProductSpider(begin_year=year)
        assert spider.begin_year == year
        assert spider.end_year == year

    def test_from_in_range_to_this_year_with_no_end(self):
        year = 2015
        spider = GSCProductSpider(begin_year=year)
        assert spider.begin_year == year
        assert spider.end_year == date.today().year

    def test_no_begin_but_end_in_range(self):
        year = 2018
        spider = GSCProductSpider(end_year=year)
        assert spider.begin_year == 2006
        assert spider.end_year == year

    def test_str_year(self):
        year = "2018"
        spider = GSCProductSpider(begin_year=year)  # type: ignore
        assert spider.begin_year == 2018

    def test_weird_year(self):
        year = (2, 0, 1, 8)
        spider = GSCProductSpider(begin_year=year)  # type: ignore
        assert spider.begin_year == 2006


def make_scrapy_response(url):
    response = rq.get(url)
    scrapy_response = HtmlResponse(body=response.content, url=url)
    return scrapy_response


class TestGscSpider:
    @pytest.fixture
    def spider(self):
        spider = GSCProductSpider(begin_year=2021)
        return spider

    def test_start_request(self, spider: GSCProductSpider):
        results = spider.start_requests()
        results = [r for r in results]
        assert len(results)
        for r in results:
            pattern = r"https://.*\.?goodsmile.info/ja/products/category/scale/announced/.*"
            assert re.match(pattern, r.url)
            assert type(r.url) is str

    def test_parsing(self, spider: GSCProductSpider):
        url = "https://www.goodsmile.info/ja/products/category/scale/announced/2021"
        scrapy_response = make_scrapy_response(url)
        results = spider.parse(scrapy_response)
        for r in results:
            pattern = r"https://www.goodsmile.info/ja/product/.*"
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_product_parsing(self, spider: GSCProductSpider):
        url = "https://www.goodsmile.info/ja/product/11942"
        scrapy_response = make_scrapy_response(url)
        result = spider.parse_product(scrapy_response)
        [product, *_] = result
        assert type(product) is Product


class TestAlterSpider:
    @pytest.fixture
    def spider(self):
        spider = AlterProductSpider(begin_year=2021)
        return spider

    def test_start_request(self, spider: AlterProductSpider):
        results = spider.start_requests()
        results = [r for r in results]
        assert len(results)
        for r in results:
            pattern = r"https://\w?.?alter-web\.jp/figure/\?yy=\d+.*"
            assert re.match(pattern, r.url)
            assert type(r.url) is str

    def test_parsing(self, spider: AlterProductSpider):
        url = "https://www.alter-web.jp/figure/?yy=2022&mm="
        scrapy_response = make_scrapy_response(url)
        results = spider.parse(scrapy_response)
        for r in results:
            pattern = r"https://\w+.?alter-web.jp/products/\d+"
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_product_parsing(self, spider: AlterProductSpider):
        url = "https://www.alter-web.jp/products/498/"
        scrapy_response = make_scrapy_response(url)
        result = spider.parse_product(scrapy_response)
        [product, *_] = result
        assert type(product) is Product
