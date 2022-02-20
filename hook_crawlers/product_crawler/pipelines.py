# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from typing import Optional
from contextlib import contextmanager

from figure_hook.database import pgsql_session
from figure_hook.Factory.model_factory import ProductModelFactory
from figure_hook.Helpers.datetime_helper import DatetimeHelper
from figure_hook.Models import Product
from figure_parser.product import Product as product_dataclass

from .spiders import ProductSpider


@contextmanager
def database_session():
    with pgsql_session() as session:
        yield session


def fetch_product(product_item: product_dataclass) -> Optional[Product]:
    product = Product.query.filter_by(
        name=product_item.name,
        id_by_official=product_item.maker_id
    ).first()

    return product


def is_product_should_be_update(
    product_model: Product,
    product_item: product_dataclass,
    spider: ProductSpider
) -> bool:
    different_checksum = not product_model.check_checksum(
        product_item.checksum)

    is_force_update = getattr(spider, 'should_force_update', False)

    return different_checksum or is_force_update


def save_product(product_item: product_dataclass):
    ProductModelFactory.createProduct(product_item)


def update_product(product_item: product_dataclass, product_model: Product):
    ProductModelFactory.updateProduct(product_item, product_model)


def fill_announced_date(product_item: product_dataclass) -> product_dataclass:
    last_release = product_item.release_infos.last()
    if last_release:
        if not last_release.announced_at:
            last_release.announced_at = DatetimeHelper.today()

    return product_item


class SaveProductInDatabasePipeline:
    def process_item(self, item: product_dataclass, spider: ProductSpider):
        is_announcement_spider = getattr(
            spider,
            'is_announcement_spider',
            False
        )
        if is_announcement_spider:
            item = fill_announced_date(item)
        with database_session():
            product = fetch_product(item)

            if product:
                should_be_updated = is_product_should_be_update(
                    product, item, spider
                )
                if should_be_updated:
                    update_product(item, product)
                    spider.log(
                        f"Successfully update data in {item.url} to database.", logging.INFO)

            if not product:
                save_product(item)
                spider.log(
                    f"Successfully save data in {item.url} to database.", logging.INFO)

        return item
