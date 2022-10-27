# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
import re
from abc import ABC
from datetime import date
from typing import Optional, Union
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup
from figure_parser.enums import (
    AlterCategory,
    BrandHost,
    GSCCategory,
    GSCLang,
    NativeCategory,
)
from figure_parser.factories import GeneralBs4ProductFactory
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider

from ..libs.helpers import JapanDatetimeHelper
from ..utils import valid_year as _valid_year

general_factory = GeneralBs4ProductFactory.create_factory()


class ProductSpider(CrawlSpider, ABC):
    def __init__(self, *args, **kwargs):
        self._force_update = kwargs.pop("force_update", False)
        self._is_announcement_spider = kwargs.pop("is_announcement_spider", False)
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

    def __init__(
        self,
        begin_year: Optional[int] = None,
        end_year: Optional[int] = None,
        lang: Optional[Union[GSCLang, str]] = None,
        category: Optional[Union[GSCCategory, str]] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        FALLBACK_BEGIN_YEAR = 2006
        FALLBACK_END_YEAR = date.today().year

        self.begin_year = _valid_year(
            begin_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, "bottom"
        )
        self.end_year = _valid_year(
            end_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, "top"
        )
        self.lang = lang or GSCLang.JAPANESE
        self.category = category or GSCCategory.SCALE

    @staticmethod
    def _extract_product_link(response):
        return LinkExtractor(
            restrict_css=".hitItem:not(.shimeproduct) > .hitBox > a"
        ).extract_links(response)

    def start_requests(self):
        period = range(self.begin_year, self.end_year + 1)
        for year in period:
            url = urljoin(
                f"https://{BrandHost.GSC}",
                f"/{self.lang}/products/category/{self.category}/announced/{year}",
            )
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        for link in self._extract_product_link(response):
            yield scrapy.Request(
                link.url,
                callback=self.parse_product,
                cookies={"age_verification_ok": "true"},
            )

    def parse_product(self, response):
        self.logger.info(f'Parsing "{response.url}"')
        page = BeautifulSoup(response.text, "lxml")
        product = general_factory.create_product(
            url=response.url,
            source=page,
        )
        yield product


class AlterProductSpider(ProductSpider):
    name = "alter_product"
    allowed_domains = [BrandHost.ALTER]

    def __init__(
        self,
        begin_year: Optional[int] = None,
        end_year: Optional[int] = None,
        category: Optional[Union[AlterCategory, str]] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        FALLBACK_BEGIN_YEAR = 2015
        FALLBACK_END_YEAR = date.today().year + 2

        self.begin_year = _valid_year(
            begin_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, "bottom"
        )
        self.end_year = _valid_year(
            end_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, "top"
        )
        self.category = category or AlterCategory.FIGURE

    def start_requests(self):
        period = range(self.begin_year, self.end_year + 1)
        self.logger.info(
            f"Period info: begin_year={self.begin_year}, end_year={self.end_year}"
        )
        for year in period:
            url = urljoin(f"https://{BrandHost.ALTER}", f"/{self.category}/?yy={year}")
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        for link in LinkExtractor(restrict_css="figure > a").extract_links(response):
            yield scrapy.Request(link.url, callback=self.parse_product)

    def parse_product(self, response):
        self.logger.info(f'Parsing "{response.url}"')
        page = BeautifulSoup(response.text, "lxml")
        product = general_factory.create_product(url=response.url, source=page)
        yield product


class NativeProductSpider(ProductSpider):
    name = "native_product"
    allowed_domains = [BrandHost.NATIVE]

    category: Union[NativeCategory, str]
    begin_page: int
    end_page: int
    max_page: int

    def __init__(
        self,
        begin_page: int = 1,
        end_page: int = 0,
        category: Optional[Union[NativeCategory, str]] = None,
        *arg,
        **kwargs,
    ) -> None:
        super().__init__(*arg, **kwargs)
        self.category = category or NativeCategory.CREATORS
        self.begin_page = int(begin_page)
        self.end_page = int(end_page) if end_page else end_page
        self.max_page = end_page

    def start_requests(self):
        url = urljoin(f"https://{BrandHost.NATIVE}", f"/{self.category}/")
        self.logger.info(
            f'Start parsing category page. (category: "{self.category}", url: "{url}")'
        )
        yield scrapy.Request(url, callback=self.parse)

    def set_max_page(self, response):
        page = BeautifulSoup(response.text, "lxml")
        pattern = r"\d\ / (?P<total>\d+)"
        count_ele = page.select_one(".pages")
        if count_ele:
            count_text = count_ele.text.strip()
            result = re.search(pattern, count_text)
            if result:
                total = result.groupdict().get("total")
                if total:
                    if total.isdigit():
                        self.max_page = int(total)

    def parse(self, response):
        self.set_max_page(response)

        end_page = self.end_page or self.max_page
        self.logger.info(
            f"Page info: begin_page={self.begin_page}, end_page={end_page}"
        )
        for page_num in range(self.begin_page, min(self.max_page, end_page) + 1):
            url = urljoin(
                f"https://{BrandHost.NATIVE}", f"/{self.category}/page/{page_num}"
            )
            yield scrapy.Request(
                url, callback=self.parse_product_urls, dont_filter=True
            )

    def parse_product_urls(self, response):
        for link in LinkExtractor(restrict_css="section > a").extract_links(response):
            yield scrapy.Request(link.url, callback=self.parse_product)

    def parse_product(self, response):
        self.logger.info(f'Parsing "{response.url}"')
        page = BeautifulSoup(response.text, "lxml")
        product = general_factory.create_product(url=response.url, source=page)
        yield product


class AmakuniProductSpider(ProductSpider):
    name = "amakuni_product"
    allowed_domains = [BrandHost.AMAKUNI]

    FALLBACK_BEGIN_YEAR = 2012
    FALLBACK_END_YEAR = JapanDatetimeHelper.today().year

    begin_year: int
    end_year: Optional[int]

    def __init__(
        self, begin_year: int = 2012, end_year: Optional[int] = None, *args, **kwargs
    ):
        FALLBACK_BEGIN_YEAR = 2012
        FALLBACK_END_YEAR = JapanDatetimeHelper.today().year

        self.begin_year = _valid_year(
            begin_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, fallback_flag="bottom"
        )
        self.end_year = end_year
        super().__init__(*args, **kwargs)

    def _validate_end_year(self, end_year: int, fallback_year: int):
        return _valid_year(
            end_year, fallback_year, self.begin_year, fallback_flag="top"
        )

    def start_requests(self):
        url = "http://amakuni.info/index.php"
        yield scrapy.Request(url, callback=self.parse)

    def set_year_range(self, response):
        page = BeautifulSoup(response.text, "lxml")
        end_year_ele = page.select_one("#top_nav > .page > li > a")

        fallback_end_year = self.FALLBACK_END_YEAR

        if end_year_ele:
            if end_year_ele.text.isdigit():
                end_year = int(end_year_ele.text)
                fallback_end_year = end_year

        self.begin_year = _valid_year(
            self.begin_year,
            fallback_end_year,
            self.FALLBACK_BEGIN_YEAR,
            fallback_flag="bottom",
        )
        self.end_year = _valid_year(
            self.end_year or fallback_end_year,
            fallback_end_year,
            self.FALLBACK_BEGIN_YEAR,
            fallback_flag="bottom",
        )

        return range(self.begin_year, self.end_year + 1)

    def parse(self, response):
        year_range = self.set_year_range(response)
        self.logger.info(f"begine_year={self.begin_year}, end_year={self.end_year}")
        for year in year_range:
            url = f"http://amakuni.info/item/item{year}.php"
            yield scrapy.Request(url, callback=self.parse_year_page)

    def parse_year_page(self, response):
        for link in LinkExtractor(
            restrict_css="#list_waku > .list_item > .list_item_right",
            deny=r"(?:2020/005)|(?:2019/013)|(?:2023/003)|(?:2023/012)|(?:2022/004)",
        ).extract_links(response):
            yield scrapy.Request(link.url, callback=self.parse_product)

    def parse_product(self, response):
        page = BeautifulSoup(response.text, "lxml")
        product = general_factory.create_product(url=response.url, source=page)
        yield product
