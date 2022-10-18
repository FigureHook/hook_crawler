# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from contextlib import suppress
from typing import Optional

from figure_hook_client import AuthenticatedClient
from figure_hook_client.models import ProductReleaseInfoInDB
from figure_parser import ProductBase, Release
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from scrapy.pipelines.images import ImagesPipeline

from .libs.checksums import generate_item_checksum
from .libs.helpers import JapanDatetimeHelper
from .repositories.product_repository import ProductRepository
from .repositories.release_repository import ReleaseRepository
from .settings import HOOK_API_ACCESS_TOKEN, HOOK_API_HOST
from .usecases.release_usecase import (
    ReleaseComparingResult,
    ReleaseInfoGroupStatus,
    ReleaseUsecase,
)

api_client = AuthenticatedClient(
    base_url=HOOK_API_HOST,
    token=HOOK_API_ACCESS_TOKEN,
    prefix="",
    auth_header_name="x-api-token",
)  # type: ignore


product_repo = ProductRepository(api_client)
release_repo = ReleaseRepository(api_client)


class S3ImagePipeline(ImagesPipeline):  # pragma: no cover
    def process_item(self, item: ProductBase, spider):
        if not isinstance(item, ProductBase):
            raise DropItem(f"Type of item: {type(item)}, expected type: {ProductBase}.")

        return super().process_item(item.dict(), spider)

    def item_completed(self, results, item, info) -> ProductBase:
        """
        Replace the images url in place.
        """
        with suppress(KeyError):
            ItemAdapter(item)[self.images_urls_field] = [x for ok, x in results if ok]  # type: ignore
        return ProductBase.parse_obj(item)


class SaveProductInDatabasePipeline:
    def persist_product(self, item: ProductBase, checksum: str, spider):
        created_product = product_repo.create_product(
            product_base=item, checksum=checksum
        )
        spider.log(
            "Successfully save data in database."
            f'(id: {created_product.id}, source: "{item.url}", name: "{created_product.name}")',
            logging.INFO,
        )

        for release in item.releases:
            created_release = release_repo.create_release_own_by_product(
                product_id=created_product.id, release=release
            )
            spider.log(
                "Successfully save release-info in database."
                f"(id: {created_release.id}, product_id: {created_product.id})",
                logging.INFO,
            )

    def update_product(self, product_id: int, item: ProductBase, checksum: str, spider):
        updated_product = product_repo.update_product(
            product_id=product_id,
            product_base=item,
            checksum=checksum,
        )
        spider.log(
            f'Successfully update data in database. (source: "{item.url}", id: {updated_product.id})',
            logging.INFO,
        )

    def update_releases(self, product_id: int, item: ProductBase, spider):
        db_releases = release_repo.get_releases_by_product_id(product_id=product_id)

        group_status = ReleaseUsecase.get_release_group_comparing_result(
            incoming_releases=item.releases, existing_releases=db_releases
        )
        if group_status is ReleaseInfoGroupStatus.CONFLICT:
            spider.logging.warning(
                "The releases data is conflicting. "
                '(source: "{}", id: {}, parsed_release_count: {},  existing_release_count: {})'.format(
                    item.url, product_id, len(item.releases), len(db_releases)
                )
            )

        elif group_status is not ReleaseInfoGroupStatus.SAME:
            if group_status is ReleaseInfoGroupStatus.NEW_RELEASE:
                for release in item.releases[len(db_releases) :]:
                    self.persist_new_release(
                        product_id=product_id,
                        release=release,
                    )

            elif group_status is ReleaseInfoGroupStatus.CHANGE:
                for in_release, existing_release in zip(item.releases, db_releases):
                    self.sync_release(
                        product_id=product_id,
                        in_release=in_release,
                        db_release=existing_release,
                    )

    def persist_new_release(self, product_id: int, release: Release):
        release_repo.create_release_own_by_product(
            product_id=product_id, release=release
        )

    def sync_release(
        self,
        product_id: int,
        in_release: Release,
        db_release: ProductReleaseInfoInDB,
    ):
        status_indicator = ReleaseUsecase.get_release_comparing_results(
            in_release=in_release, db_release=db_release
        )
        if ReleaseComparingResult.IGNORE in status_indicator:
            return

        release_update = ReleaseUsecase.build_release_patch_data_by_status(
            incoming_release=in_release,
            status_indicator=status_indicator,
        )
        release_repo.update_release(
            product_id=product_id,
            release_id=db_release.id,
            release=release_update,
        )

    def process_item(self, item: ProductBase, spider):
        assert isinstance(item, ProductBase)
        if is_announcement_spider(spider):
            item = fill_announced_date(item)

        product_meta_checksum = generate_item_checksum(item)
        product_in_db = product_repo.get_product_by_url(source_url=item.url)

        if not product_in_db:
            try:
                self.persist_product(
                    item=item, checksum=product_meta_checksum, spider=spider
                )

            except Exception as e:
                spider.logger.error(
                    f'Exception when saving new product to database. (source: "{item.url}")'
                )
                spider.logger.error(e)

            return item

        if product_in_db.checksum != product_meta_checksum:
            try:
                self.update_product(
                    product_id=product_in_db.id,
                    item=item,
                    checksum=product_meta_checksum,
                    spider=spider,
                )
                self.update_releases(
                    product_id=product_in_db.id, item=item, spider=spider
                )

            except Exception as e:
                spider.logger.error(
                    f'Exception when updating product in database. (source: "{item.url}")'
                )
                spider.logger.error(e)

        try:
            self.update_releases(product_id=product_in_db.id, item=item, spider=spider)
        except Exception as e:
            spider.logger.error(
                "Exception when updating product release-infos in database."
                f'(source: "{item.url}", product_id: {product_in_db.id})'
            )
            spider.logger.error(e)

        return item


def get_last_release(product_item: ProductBase) -> Optional[Release]:
    releases = product_item.releases
    if releases:
        if len(releases):
            return releases[-1]
    return None


def fill_announced_date(product: ProductBase) -> ProductBase:
    last_release = get_last_release(product)
    if last_release:
        last_release.announced_at = JapanDatetimeHelper.today()
    return product


def is_announcement_spider(spider) -> bool:
    return getattr(spider, "is_announcement_spider", False)
