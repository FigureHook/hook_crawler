import re
import urllib.parse
from abc import ABC
from typing import Iterable, Literal, Optional

import scrapy
from bs4 import BeautifulSoup
from figure_hook.database import pgsql_session
from figure_hook.Models import Product
from figure_parser.constants import BrandHost
from figure_parser.factory import GSCFactory
from figure_parser.utils import RelativeUrl
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from sqlalchemy import and_, select


class GscDelayPostAbstractSpider(CrawlSpider, ABC):
    allowed_domains = [BrandHost.GSC]
    start_urls = [
        'https://www.goodsmile.info/ja/posts/category/information/date/'
    ]

    rules = [
        Rule(
            LinkExtractor(
                allow='(' +
                f'{urllib.parse.quote("発売月")}|' +
                f'{urllib.parse.quote("発売時期")}|' +
                f'{urllib.parse.quote("発売延期")}|' +
                f'{urllib.parse.quote("延期")}' +
                ')',
                unique=True
            ),
            callback='parse_delay_post'
        )
    ]

    def parse_delay_post(self, response):
        page = BeautifulSoup(response.text, 'lxml')
        products_delayed = _parse_delay_products_from_post(page)

        products_recorded_in_db = fetch_gsc_products_by_official_id(
            products_delayed.keys()
        )

        for p_id in set(products_delayed) & products_recorded_in_db:
            yield scrapy.Request(
                RelativeUrl.gsc(products_delayed[p_id]['url']),
                callback=self.parse_product,
                cb_kwargs={"jan": products_delayed[p_id]['jan']},
                cookies={
                    "age_verification_ok": "true"
                }
            )

    def parse_product(self, response, jan):
        self.logger.info(f"Parsing {response.url}...")
        page = BeautifulSoup(response.text, "lxml")
        product = GSCFactory.create_product(
            response.url,
            page=page,
            is_normalized=True,
            speculate_announce_date=True
        )
        product.jan = jan
        yield product

    def add_rule(self, rule: Rule):
        rules = list(self.rules)
        rules.append(rule)
        self.rules = rules


class GscNewDelayPostSpider(GscDelayPostAbstractSpider):
    name = 'gsc_new_delay_post'

    def parse(self, response, **kwargs):
        page = BeautifulSoup(response.text, 'lxml')
        new_post_links = [
            RelativeUrl.gsc(icon.parent.get('href'))
            for icon in page.select(".newsS > a > .newicon")
            if icon.parent
        ]
        for link in new_post_links:
            yield scrapy.Request(link)


class GscDelayPostSpider(GscDelayPostAbstractSpider):
    name = 'gsc_delay_post'

    def __init__(self, begin_year: Optional[int] = None, end_year: Optional[int] = None, *args, **kwargs):
        year_pattern = r"\d+"
        if begin_year and end_year:
            year_pattern = range_to_regex(int(begin_year), int(end_year))

        self.add_rule(
            Rule(
                LinkExtractor(
                    allow=fr'https://.*\.?goodsmile.info/ja/posts/category/information/date/{year_pattern}$',
                    unique=True,
                ),
            ),
        )

        super().__init__(*args, **kwargs)


def fetch_gsc_products_by_official_id(ids: Iterable) -> set[str]:
    products_recorded_in_db = set()
    with pgsql_session() as session:
        stmt = select(
            Product.url.label('url'),
            Product.jan.label('jan'),
            Product.id_by_official.label('id_by_official')
        ).where(
            and_(
                Product.url.like("%goodsmile%"),
                Product.id_by_official.in_(ids)
            )
        ).select_from(Product)

        products = session.execute(stmt).all()
        for p in products:
            products_recorded_in_db.add(p.id_by_official)

    return products_recorded_in_db


def range_to_regex(begin: int, end: int):
    range_pattern = r"|".join([str(num) for num in range(begin, end+1)])
    return f"({range_pattern})"


DelayTag = dict[str, dict[Literal['jan', 'url'], str]]


def _parse_delay_products_from_post(page: BeautifulSoup) -> DelayTag:
    products_delayed: DelayTag = {}

    for e in page.findAll('br'):
        e.extract()

    changed_ps = page.select(
        ".content > p, .content > center", string=re.compile("発売[月|日]変更")
    )
    for c in changed_ps:
        if 'JAN' in c.get_text():
            results = re.findall(
                r"「.*href=\"(.*\/product\/(\d+)\/.*)\".*」JAN：(\d+)", str(c)
            )
            for r in results:
                url = r[0]
                maker_id = r[1]
                jan = r[2]
                products_delayed[maker_id] = {
                    'url': url,
                    'jan': jan
                }

    return products_delayed
