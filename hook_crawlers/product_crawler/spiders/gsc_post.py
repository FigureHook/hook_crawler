import re
import urllib.parse
from abc import ABC
from typing import Iterable, Literal, Optional
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup
from figure_parser.enums import BrandHost
from figure_parser.factories import GeneralBs4ProductFactory
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

DelayTag = dict[str, dict[Literal["jan", "url"], str]]

general_factory = GeneralBs4ProductFactory.create_factory()


class GscDelayPostAbstractSpider(CrawlSpider, ABC):
    allowed_domains = [BrandHost.GSC]
    start_urls = ["https://www.goodsmile.info/ja/posts/category/information/date/"]

    rules = [
        Rule(
            LinkExtractor(
                allow="("
                f'{urllib.parse.quote("発売月")}|'
                f'{urllib.parse.quote("発売時期")}|'
                f'{urllib.parse.quote("発売延期")}|'
                f'{urllib.parse.quote("延期")}'
                ")",
                unique=True,
            ),
            callback="parse_delay_post",
        )
    ]

    @staticmethod
    def fetch_gsc_products_by_official_id(ids: Iterable) -> set[str]:
        return set(ids)

    @staticmethod
    def _parse_delay_products_from_post(page: BeautifulSoup) -> DelayTag:
        products_delayed: DelayTag = {}

        for e in page.findAll("br"):
            e.extract()

        changed_ps = page.select(
            ".content > p, .content > center", string=re.compile("発売[月|日]変更")
        )
        for c in changed_ps:
            if "JAN" in c.get_text():
                results = re.findall(
                    r"「.*href=\"(.*\/product\/(\d+)\/.*)\".*」JAN：(\d+)", str(c)
                )
                for r in results:
                    url = r[0]
                    maker_id = r[1]
                    jan = r[2]
                    products_delayed[maker_id] = {"url": url, "jan": jan}

        return products_delayed

    def parse_delay_post(self, response):
        page = BeautifulSoup(response.text, "lxml")
        products_delayed = self._parse_delay_products_from_post(page)

        products_recorded_in_db = self.fetch_gsc_products_by_official_id(
            products_delayed.keys()
        )

        for p_id in set(products_delayed) & products_recorded_in_db:
            url = urljoin(
                f"https://{BrandHost.GSC}",
                products_delayed[p_id]["url"],
            )
            yield scrapy.Request(
                url=url,
                callback=self.parse_product,
                cb_kwargs={"jan": products_delayed[p_id]["jan"]},
                cookies={"age_verification_ok": "true"},
            )

    def parse_product(self, response, jan):
        self.logger.info(f"Parsing {response.url}...")
        page = BeautifulSoup(response.text, "lxml")
        product = general_factory.create_product(url=response.url, source=page)
        product.jan = jan
        yield product

    def add_rule(self, rule: Rule):
        rules = list(self.rules)
        rules.append(rule)
        self.rules = rules


class GscNewDelayPostSpider(GscDelayPostAbstractSpider):
    name = "gsc_new_delay_post"

    def parse(self, response, **kwargs):
        page = BeautifulSoup(response.text, "lxml")
        for icon in page.select(".newsS > a > .newicon"):
            if icon.parent:
                href = icon.parent.get("href")
                if type(href) is str:
                    yield scrapy.Request(
                        urljoin(
                            f"https://{BrandHost.GSC}",
                            href,
                        )
                    )


class GscDelayPostSpider(GscDelayPostAbstractSpider):
    name = "gsc_delay_post"

    def __init__(
        self,
        begin_year: Optional[int] = None,
        end_year: Optional[int] = None,
        *args,
        **kwargs,
    ):
        year_pattern = r"\d+"
        if begin_year and end_year:
            year_pattern = range_to_regex(int(begin_year), int(end_year))

        self.add_rule(
            Rule(
                LinkExtractor(
                    allow=rf"https://.*\.?goodsmile.info/ja/posts/category/information/date/{year_pattern}$",
                    unique=True,
                ),
            ),
        )

        super().__init__(*args, **kwargs)


def range_to_regex(begin: int, end: int):
    range_pattern = r"|".join([str(num) for num in range(begin, end + 1)])
    return f"({range_pattern})"
