# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
from abc import ABC
from datetime import date
from typing import Literal, Optional, Union

import scrapy
from bs4 import BeautifulSoup
from figure_parser.constants import (AlterCategory, BrandHost, GSCCategory,
                                     GSCLang, NativeCategory)
from figure_parser.factory import AlterFactory, GSCFactory, NativeFactory
from figure_parser.native.announcement_parser import get_max_page_count
from figure_parser.utils import RelativeUrl
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider

from ..utils import valid_year as _valid_year


def _gsc_product_link_extractor(res):
    return LinkExtractor(
        restrict_css=".hitItem:not(.shimeproduct) > .hitBox > a"
    ).extract_links(res)


class ProductSpider(CrawlSpider, ABC):
    def __init__(self, *args, **kwargs):
        self._force_update = kwargs.pop("force_update", False)
        self._is_announcement_spider = kwargs.pop(
            "is_announcement_spider", False
        )
        super().__init__(*args, **kwargs)

    @property
    def should_force_update(self):
        return self._force_update

    @property
    def is_announcement_spider(self):
        return self._is_announcement_spider


class GSCProductSpider(ProductSpider):
    name = "gsc_product"
    allowed_domains = [BrandHost.GSC]

    def __init__(self,
                 begin_year: Optional[int] = None,
                 end_year: Optional[int] = None,
                 lang: Optional[Union[GSCLang, str]] = None,
                 category: Optional[Union[GSCCategory, str]] = None,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        FALLBACK_BEGIN_YEAR = 2006
        FALLBACK_END_YEAR = date.today().year

        self.begin_year = _valid_year(
            begin_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, 'bottom'
        )
        self.end_year = _valid_year(
            end_year, FALLBACK_END_YEAR,  FALLBACK_BEGIN_YEAR, 'top'
        )
        self.lang = lang or GSCLang.JAPANESE
        self.category = category or GSCCategory.SCALE

    def start_requests(self):
        period = range(self.begin_year, self.end_year+1)
        for year in period:
            url = RelativeUrl.gsc(
                f"/{self.lang}/products/category/{self.category}/announced/{year}"
            )
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        for link in LinkExtractor(restrict_css=".hitItem:not(.shimeproduct) > .hitBox > a").extract_links(response):
            yield scrapy.Request(link.url, callback=self.parse_product, cookies={
                "age_verification_ok": "true"
            })

    def parse_product(self, response):
        self.logger.info(f"Parsing {response.url}...")
        page = BeautifulSoup(response.text, "lxml")
        product = GSCFactory.create_product(
            response.url,
            page=page,
            is_normalized=True,
            speculate_announce_date=True
        )
        yield product


class AlterProductSpider(ProductSpider):
    name = "alter_product"
    allowed_domains = [BrandHost.ALTER]

    def __init__(self,
                 begin_year: Optional[int] = None,
                 end_year: Optional[int] = None,
                 category: Optional[Union[AlterCategory, str]] = None,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        FALLBACK_BEGIN_YEAR = 2015
        FALLBACK_END_YEAR = date.today().year + 2

        self.begin_year = _valid_year(
            begin_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, 'bottom'
        )
        self.end_year = _valid_year(
            end_year, FALLBACK_END_YEAR,  FALLBACK_BEGIN_YEAR, 'top'
        )
        self.category = category or AlterCategory.FIGURE

    def start_requests(self):
        period = range(self.begin_year, self.end_year+1)
        for year in period:
            url = RelativeUrl.alter(f"/{self.category}/?yy={year}")
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        for link in LinkExtractor(restrict_css="figure > a").extract_links(response):
            yield scrapy.Request(link.url, callback=self.parse_product)

    def parse_product(self, response):
        self.logger.info(f"Parsing {response.url}...")
        page = BeautifulSoup(response.text, "lxml")
        product = AlterFactory.create_product(
            response.url, page=page, is_normalized=True)
        yield product


class NativeProductSpider(ProductSpider):
    name = "native_product"
    allowed_domains = [BrandHost.NATIVE]

    def __init__(
            self,
            begin_page: int = 1,
            end_page: Optional[int] = None,
            category: Optional[Union[NativeCategory, str]] = None,
            *arg,  **kwargs) -> None:
        super().__init__(*arg, **kwargs)
        self.category = category or NativeCategory.CREATORS
        self.begin_page = int(begin_page)
        self.end_page = int(end_page) if end_page else end_page

    def start_requests(self):
        url = RelativeUrl.native(
            f"/{self.category}/"
        )
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        page = BeautifulSoup(response.text, "lxml")
        if not self.end_page:
            self.end_page = get_max_page_count(page)

        for page_num in range(self.begin_page, self.end_page+1):
            url = RelativeUrl.native(
                f"/{self.category}/page/{page_num}"
            )
            yield scrapy.Request(url, callback=self.parse_product_url, dont_filter=True)

    def parse_product_url(self, response):
        for link in LinkExtractor(restrict_css="section > a").extract_links(response):
            yield scrapy.Request(link.url, callback=self.parse_product)

    def parse_product(self, response):
        self.logger.info(f"Parsing {response.url}...")
        page = BeautifulSoup(response.text, "lxml")
        product = NativeFactory.create_product(
            response.url, page=page, is_normalized=True, speculate_announce_date=True)
        yield product
