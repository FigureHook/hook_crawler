# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
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


def _gsc_product_link_extractor(res):
    return LinkExtractor(
        restrict_css=".hitItem:not(.shimeproduct) > .hitBox > a"
    ).extract_links(res)


def _valid_year(
    year,
    top: int,
    bottom: int,
    fallback_flag: Literal['top', 'bottom']
) -> int:
    is_int = type(year) is int

    def _fallback(year, flag):
        if flag == 'top':
            return top
        if flag == 'bottom':
            return bottom
        return year

    if is_int:
        is_in_range = bottom <= year <= top
        if not is_in_range:
            year = _fallback(year, fallback_flag)

    if not is_int:
        try:
            year = int(year)
        except:
            year = _fallback(year, fallback_flag)

    return year


class GSCProductSpider(CrawlSpider):
    name = "gsc_product"
    allowed_domains = [BrandHost.GSC]

    def __init__(self,
                 begin_year: Optional[int] = None,
                 end_year: Optional[int] = None,
                 lang: Optional[Union[GSCLang, str]] = None,
                 category: Optional[Union[GSCCategory, str]] = None,
                 force_update: bool = False,
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
        self._force_update = force_update

    @property
    def force_update(self):
        return self._force_update

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


class AlterProductSpider(CrawlSpider):
    name = "alter_product"
    allowed_domains = [BrandHost.ALTER]

    def __init__(self,
                 begin_year: Optional[int] = None,
                 end_year: Optional[int] = None,
                 category: Optional[Union[AlterCategory, str]] = None,
                 force_update: bool = False,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        FALLBACK_BEGIN_YEAR = 2015
        FALLBACK_END_YEAR = date.today().year + 2

        self.begin_year = _valid_year(
            begin_year, FALLBACK_BEGIN_YEAR, FALLBACK_END_YEAR, 'bottom'
        )
        self.end_year = _valid_year(
            end_year, FALLBACK_BEGIN_YEAR,  FALLBACK_END_YEAR, 'top'
        )
        self.category = category or AlterCategory.FIGURE
        self._force_update = force_update

    @property
    def force_update(self):
        return self._force_update

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


class NativeProductSpider(CrawlSpider):
    name = "native_product"
    allowed_domains = [BrandHost.NATIVE]

    def __init__(
            self,
            category: Optional[Union[AlterCategory, str]] = None,
            begin_page: int = 1,
            end_page: Optional[int] = None,
            force_update: bool = False,
            *arg,  **kwargs) -> None:
        super().__init__(*arg, **kwargs)
        self.category = category or NativeCategory.CREATORS
        self.begin_page = begin_page
        self.end_page = end_page
        self._force_update = force_update

    @property
    def force_update(self):
        return self._force_update

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


class GSCRecentProductSpider(GSCProductSpider):
    name = "gsc_recent"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(begin_year=date.today().year, *args, **kwargs)


class AlterRecentProductSpider(AlterProductSpider):
    name = "alter_recent"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(category=AlterCategory.ALL,
                         begin_year=date.today().year, *args, **kwargs)


class NativeRecentCharacterSpider(NativeProductSpider):
    name = "native_character_recent"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(category=NativeCategory.CHARACTERS,
                         begin_page=1, end_page=1, *args, **kwargs)


class NativeRecentCreatorSpider(NativeProductSpider):
    name = "native_creator_recent"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(category=NativeCategory.CREATORS,
                         begin_page=1, end_page=1, *args, **kwargs)
