from datetime import date

import pytest
from figure_hook.database import pgsql_session
from figure_hook.Factory.model_factory import ProductModelFactory
from figure_hook.Helpers.datetime_helper import DatetimeHelper
from figure_parser.product import Product
from hook_crawlers.product_crawler.pipelines import \
    SaveProductInDatabasePipeline
from hook_crawlers.product_crawler.spiders import ProductSpider
from pytest_mock import MockerFixture


class MockProductSpider(ProductSpider):
    name = "mocker"


@pytest.mark.usefixtures("session", "product")
class TestSaveDataToDBPipeline:
    pipeline = SaveProductInDatabasePipeline()

    def test_announcement_spider_with_no_announced_date_product(self, product: Product):
        spider = MockProductSpider(is_announcement_spider=True)

        p = self.pipeline.process_item(product, spider)
        release = p.release_infos.last()
        if release:
            assert release.announced_at == DatetimeHelper.today()

    def test_announcement_spider_with_announced_date_product(self, product: Product):
        spider = MockProductSpider(is_announcement_spider=True)

        plr = product.release_infos.last()
        if plr:
            plr.announced_at = date(2020, 11, 1)

        p = self.pipeline.process_item(product, spider)
        release = p.release_infos.last()
        if release:
            assert release.announced_at != DatetimeHelper.today()

    def test_new_product(self, product: Product, mocker: MockerFixture):
        spider = MockProductSpider(is_announcement_spider=True)
        product_creation = mocker.patch(
            'figure_hook.Factory.model_factory.ProductModelFactory.createProduct'
        )
        product_update = mocker.patch(
            'figure_hook.Factory.model_factory.ProductModelFactory.updateProduct'
        )
        product_item = self.pipeline.process_item(product, spider)
        product_creation.assert_called_once_with(product_item)
        product_update.assert_not_called()

    def test_existed_product(self, product: Product, mocker: MockerFixture):
        spider = MockProductSpider(is_announcement_spider=True)
        with pgsql_session():
            ProductModelFactory.createProduct(product)

        product_creation = mocker.patch(
            'figure_hook.Factory.model_factory.ProductModelFactory.createProduct'
        )
        product_update = mocker.patch(
            'figure_hook.Factory.model_factory.ProductModelFactory.updateProduct'
        )
        self.pipeline.process_item(product, spider)
        product_creation.assert_not_called()
        product_update.assert_called_once()
