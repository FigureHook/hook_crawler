# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from contextlib import contextmanager
from typing import Dict, Optional, TypeVar

from dacite.core import from_dict
from figure_hook.database import pgsql_session
from figure_hook.Factory.model_factory import ProductModelFactory
from figure_hook.Helpers.datetime_helper import DatetimeHelper
from figure_hook.Models import Product
from figure_parser.product import Product as product_dataclass
from scrapy.pipelines.images import ImagesPipeline

from .spiders import ProductSpider


class S3ImagePipeline(ImagesPipeline):
    def process_item(self, item: product_dataclass, spider):
        return super().process_item(item.as_dict(), spider)


class RestoreProductFromDictPipeline:
    """
    In this pipeline, items' image urls would be changed to s3 image url.
    """

    def process_item(self, item: Dict, spider):
        from .settings import IMAGES_RESULT_FIELD
        item = replace_images_urls_to_s3_urls(item, IMAGES_RESULT_FIELD)
        return from_dict(data_class=product_dataclass, data=item)


D_T = TypeVar('D_T', bound=Dict)


def replace_images_urls_to_s3_urls(product_compatible_item: D_T, s3_url_field: str) -> D_T:
    if product_compatible_item[s3_url_field]:
        s3_url_mapping: Dict[str, str] = {}
        for s3_item in product_compatible_item[s3_url_field]:
            s3_url_mapping[s3_item['url']] = s3_item['path']

        for index, url in enumerate(product_compatible_item['images']):
            product_compatible_item['images'][index] = s3_url_mapping[url]

    return product_compatible_item


class SaveProductInDatabasePipeline:
    def process_item(self, item: product_dataclass, spider: ProductSpider):
        """item is Product compatiable dict"""

        if is_announcement_spider(spider):
            item = fill_announced_date(item)

        with database_session():
            product = fetch_product(item)

            if product:
                if product_should_be_updated(
                    product, item, spider
                ):
                    update_product(item, product)
                    spider.log(
                        f"Successfully update data in {item.url} to database.",
                        logging.INFO
                    )

            if not product:
                save_product(item)
                spider.log(
                    f"Successfully save data in {item.url} to database.",
                    logging.INFO
                )

        return item


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


def product_should_be_updated(
    product_model: Product,
    product_item: product_dataclass,
    spider: ProductSpider
) -> bool:
    different_checksum = not product_model.check_checksum(
        product_item.checksum)

    is_force_update = getattr(spider, 'should_force_update', False)

    return different_checksum or is_force_update


def save_product(product_item: product_dataclass):
    ProductModelFactory.create_product(product_item)


def update_product(product_item: product_dataclass, product_model: Product):
    ProductModelFactory.update_product(product_item, product_model)


def fill_announced_date(product_item: product_dataclass) -> product_dataclass:
    last_release = product_item.release_infos.last()
    if last_release:
        if not last_release.announced_at:
            last_release.announced_at = DatetimeHelper.today()

    return product_item


def is_announcement_spider(spider) -> bool:
    return getattr(
        spider,
        'is_announcement_spider',
        False
    )
