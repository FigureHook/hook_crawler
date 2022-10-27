import re
from datetime import date

import pytest
import requests as rq
from figure_parser import ProductBase
from pytest_mock import MockerFixture
from scrapy.http import HtmlResponse

from hook_crawlers.product_crawler.spiders import (
    AlterProductSpider,
    AmakuniProductSpider,
    GSCProductSpider,
    NativeProductSpider,
)


class TestYearValidation:
    def test_begin_is_end(self):
        year = date.today().year
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
        pattern = r"https://.*\.?goodsmile.info/ja/products/category/scale/announced/.*"
        for r in results:
            assert re.match(pattern, r.url)
            assert type(r.url) is str

    def test_parsing(self, spider: GSCProductSpider):
        url = "https://www.goodsmile.info/ja/products/category/scale/announced/2021"
        scrapy_response = make_scrapy_response(url)
        results = spider.parse(scrapy_response)
        pattern = r"https://www.goodsmile.info/ja/product/.*"
        for r in results:
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_product_parsing(self, spider: GSCProductSpider):
        url = "https://www.goodsmile.info/ja/product/11942"
        scrapy_response = make_scrapy_response(url)
        result = spider.parse_product(scrapy_response)
        [product, *_] = result
        assert type(product) is ProductBase


class TestGscDelaySpider:
    def test_year_range_regex_transformation(self):
        from hook_crawlers.product_crawler.spiders.gsc_post import range_to_regex

        assert range_to_regex(2002, 2005) == r"(2002|2003|2004|2005)"

    def test_parse_delay_post(self, mocker: MockerFixture):
        from hook_crawlers.product_crawler.spiders.gsc_post import GscDelayPostSpider

        spider = GscDelayPostSpider(begin_year=2022, end_year=2022)
        # =========mocker setting=========
        mocker.patch.object(
            spider,
            "fetch_gsc_products_by_official_id",
            new_callable=lambda: lambda x: set(x),
        )
        # =========mocker setting=========

        scrapy_response = make_scrapy_response(
            "https://www.goodsmile.info/ja/post/5280/"
            "2021%E5%B9%B41%E6%9C%88%E7%99%BA%E5%A3%B2"
            "%E4%BA%88%E5%AE%9A%E5%95%86%E5%93%81%E3%81%AE"
            "%E5%BB%B6%E6%9C%9F%E9%80%A3%E7%B5%A1%E3%81%A8%E3%81%8A%E8%A9%AB%E3%81%B3.html"
        )

        results = spider.parse_delay_post(scrapy_response)
        results = [r for r in results]
        assert len(results)
        pattern = r"https://.*\.?goodsmile.info/ja/product/.*"
        for r in results:
            assert "jan" in r.cb_kwargs, "Should call callback with `jan` argument."
            assert re.match(pattern, r.url), "Not a valid url."
            assert type(r.url) is str

    def test_product_parsing(self):
        from hook_crawlers.product_crawler.spiders.gsc_post import GscDelayPostSpider

        spider = GscDelayPostSpider(begin_year=2022, end_year=2022)
        jan = "4580416923453"
        url = "https://www.goodsmile.info/ja/product/10419"
        scrapy_response = make_scrapy_response(url)
        result = spider.parse_product(scrapy_response, jan=jan)
        [product, *_] = result
        assert type(product) is ProductBase
        assert product.jan == jan, "JAN didn't match with input value."


class TestAlterSpider:
    @pytest.fixture
    def spider(self):
        spider = AlterProductSpider(begin_year=2021)
        return spider

    def test_start_request(self, spider: AlterProductSpider):
        results = spider.start_requests()
        results = [r for r in results]
        assert len(results)
        pattern = r"https://.*\.?alter-web\.jp/figure/\?yy=\d+.*"
        for r in results:
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_parsing(self, spider: AlterProductSpider):
        url = "https://www.alter-web.jp/figure/?yy=2022&mm="
        scrapy_response = make_scrapy_response(url)
        results = spider.parse(scrapy_response)
        pattern = r"https://.*\.?alter-web.jp/products/\d+"
        for r in results:
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_product_parsing(self, spider: AlterProductSpider):
        url = "https://www.alter-web.jp/products/498/"
        scrapy_response = make_scrapy_response(url)
        result = spider.parse_product(scrapy_response)
        [product, *_] = result
        assert type(product) is ProductBase


class TestNativeSpider:
    @pytest.fixture
    def spider(self):
        spider = NativeProductSpider(begin_page=1)
        return spider

    def test_start_request(self, spider: NativeProductSpider):
        results = spider.start_requests()
        results = [r for r in results]
        assert len(results)
        pattern = r"https://.*\.?native-web.jp/\w+?/[page/\d+]?"
        for r in results:
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_parsing(self, spider: NativeProductSpider):
        url = "https://www.native-web.jp/creators/"
        scrapy_response = make_scrapy_response(url)
        results = spider.parse(scrapy_response)
        pattern = r"https://.*\.?native-web.jp/\w+?/[page/\d+]?"
        for r in results:
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_parsing_product_url(self, spider: NativeProductSpider):
        spider.end_page = 1
        spider.max_page = 10
        url = "https://www.native-web.jp/creators/"
        scrapy_response = make_scrapy_response(url)
        results = spider.parse(scrapy_response)
        pattern = r"https://.*\.?native-web.jp/\w+?/[page/\d+]?"
        for r in results:
            assert type(r.url) is str
            assert re.match(pattern, r.url)

    def test_product_parsing(self, spider: NativeProductSpider):
        url = "https://www.native-web.jp/creators/4891/"
        scrapy_response = make_scrapy_response(url)
        result = spider.parse_product(scrapy_response)
        [product, *_] = result
        assert type(product) is ProductBase

    def test_set_max_page(self, spider: NativeProductSpider):
        url = "https://www.native-web.jp/creators/"
        scrapy_response = make_scrapy_response(url)
        spider.set_max_page(scrapy_response)
        assert spider.max_page > 0

    def test_product_link_parsing(self, spider: NativeProductSpider):
        url = "https://www.native-web.jp/creators/page/4/"
        scrapy_response = make_scrapy_response(url)
        results = spider.parse_product_urls(scrapy_response)
        product_pattern = r"https://.*\.?native-web.jp/\w+?/\d+"
        for r in results:
            assert re.match(product_pattern, r.url)


class TestAmakuniSpider:
    @pytest.fixture
    def spider(self):
        spider = AmakuniProductSpider()
        return spider

    def test_start_request(self, spider: AmakuniProductSpider):
        results = spider.start_requests()
        url_pattern = r"http://amakuni.info/index.php"
        for r in results:
            assert re.match(url_pattern, r.url)

    def test_parser_year_page(self, spider: AmakuniProductSpider):
        url = "http://amakuni.info/item/item2023.php"
        resp = make_scrapy_response(url)
        product_url_pattern = r"http://amakuni\.info/item/\d+/.+\.php"
        results = spider.parse_year_page(resp)
        for r in results:
            assert re.match(product_url_pattern, r.url)

    def test_parse_product(self, spider: AmakuniProductSpider):
        url = "http://amakuni.info/item/2023/022.php"
        resp = make_scrapy_response(url)
        result = spider.parse_product(resp)
        product, *_ = result
        assert isinstance(product, ProductBase)
