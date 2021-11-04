# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from typing import Union

from figure_hook.database import pgsql_session
from figure_hook.Factory.model_factory import ProductModelFactory
from figure_hook.Helpers.datetime_helper import DatetimeHelper
from figure_hook.Models import Product
from figure_parser.product import Product as product_dataclass
from scrapy.spiders.crawl import CrawlSpider


class SaveProductInDatabasePipeline:
    def process_item(self, item: product_dataclass, spider: CrawlSpider):
        new_keyword = "recent"
        if spider.name:
            if new_keyword in spider.name:
                last_release = item.release_infos.last()
                if last_release:
                    if not last_release.announced_at:
                        last_release.announced_at = DatetimeHelper.today()
        with pgsql_session():
            product: Union[Product, None] = Product.query.filter_by(
                name=item.name,
                id_by_official=item.maker_id
            ).first()

            if product:
                should_be_updated = any(
                    (
                        not product.check_checksum(item.checksum),
                        spider.force_update
                    )
                )
                if should_be_updated:
                    product = ProductModelFactory.updateProduct(item, product)
                    spider.log(f"Successfully update data in {item.url} to database.", logging.INFO)

            if not product:
                product = ProductModelFactory.createProduct(item)
                spider.log(f"Successfully save data in {item.url} to database.", logging.INFO)

        return item
