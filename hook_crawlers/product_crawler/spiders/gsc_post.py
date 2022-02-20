import re
import urllib.parse
from datetime import date
from typing import Iterable, Optional

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

from ..utils import valid_year as _valid_year


class GscDelayPostSpider(CrawlSpider):
    name = 'gsc_delay_post'
    allowed_domains = [BrandHost.GSC]
    start_urls = [
        'https://www.goodsmile.info/ja/posts/category/information/date/'
    ]

    def __init__(self, begin_year: Optional[int] = None,
                 end_year: Optional[int] = None, *a, **kw):

        FALLBACK_BEGIN_YEAR = 2007
        FALLBACK_END_YEAR = date.today().year
        self.begin_year = _valid_year(
            begin_year, FALLBACK_END_YEAR, FALLBACK_BEGIN_YEAR, 'bottom'
        )
        self.end_year = _valid_year(
            end_year, FALLBACK_END_YEAR,  FALLBACK_BEGIN_YEAR, 'top'
        )

        def filter_annual(url: str):
            pattern = r"https://.*\.?goodsmile.info/ja/posts/category/information/date/(\d+)$"
            result = re.search(pattern, url)
            if result:
                if int(result.group(1)) in range(self.begin_year, self.end_year+1):
                    return url
            return None

        self.rules = [
            Rule(
                LinkExtractor(
                    allow=r'https://.*\.?goodsmile.info/ja/posts/category/information/date/\d+$',
                    process_value=filter_annual
                ),
                callback='parse'
            ),
            Rule(
                LinkExtractor(
                    allow=fr'[{urllib.parse.quote("発売月")}|{urllib.parse.quote("発売時期")}|{urllib.parse.quote("発売延期")}|{urllib.parse.quote("延期")}]'
                ),
                callback='parse_delay_post'
            )
        ]
        super().__init__(*a, **kw)

    def parse_delay_post(self, response):
        products_delayed = {}
        product_delayed_ids = set()
        page = BeautifulSoup(response.text, 'lxml')

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
                    product_delayed_ids.add(maker_id)

        products_recorded_in_db = fetch_gsc_products_by_official_id(
            product_delayed_ids
        )

        for p_id in product_delayed_ids & products_recorded_in_db:
            yield scrapy.Request(
                RelativeUrl.gsc(products_delayed[p_id]['url']),
                callback=self.parse_product,
                cb_kwargs={"jan": products_delayed[p_id]['jan']}
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

        products: list[Product] = session.execute(stmt).all()
        for p in products:
            products_recorded_in_db.add(p.id_by_official)

    return products_recorded_in_db
