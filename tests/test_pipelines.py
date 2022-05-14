from datetime import date

import pytest
from figure_parser.product import Product
from hook_crawlers.product_crawler.pipelines import (
    SaveProductInDatabasePipeline, fill_announced_date,
    product_should_be_updated)
from hook_crawlers.product_crawler.spiders import ProductSpider
from pytest_mock import MockerFixture


class MockProductSpider(ProductSpider):
    name = "mocker"


class MockProductModel:
    def __init__(self, checksum):
        self.checksum = checksum

    def check_checksum(self, checksum):
        return self.checksum


@pytest.mark.usefixtures("product")
class TestSaveDataToDBPipeline:
    pipeline = SaveProductInDatabasePipeline()

    @pytest.fixture
    def mock_db_session(self, mocker: MockerFixture):
        mocker.patch(
            'hook_crawlers.product_crawler.pipelines.database_session')

    def test_announced_date_filling(self, product: Product):
        p = fill_announced_date(product)
        release = p.release_infos.last()
        if release:
            assert release.announced_at
            release.announced_at = date(2020, 11, 1)
            p = fill_announced_date(product)
            assert release.announced_at == date(2020, 11, 1)

    def test_should_product_be_updated(self, product: Product):
        spider = MockProductSpider(is_announcement_spider=True)
        force_spider = MockProductSpider(force_update=True)
        p1 = MockProductModel(True)
        p2 = MockProductModel(False)

        assert not product_should_be_updated(
            p1, product, spider  # type: ignore
        )
        assert product_should_be_updated(
            p1, product, force_spider  # type: ignore
        )

        assert product_should_be_updated(p2, product, spider)  # type: ignore

    def test_new_product(self, product: Product, mocker: MockerFixture, mock_db_session):
        spider = MockProductSpider(is_announcement_spider=True)
        mocker.patch(
            'hook_crawlers.product_crawler.pipelines.fetch_product', return_value=False)
        product_creation = mocker.patch(
            'hook_crawlers.product_crawler.pipelines.save_product'
        )
        product_update = mocker.patch(
            'hook_crawlers.product_crawler.pipelines.update_product'
        )
        product_item = self.pipeline.process_item(product, spider)
        product_creation.assert_called_once_with(product_item)
        product_update.assert_not_called()

    def test_existed_product(self, product: Product, mocker: MockerFixture, mock_db_session):
        spider = MockProductSpider(is_announcement_spider=True)
        mocker.patch(
            'hook_crawlers.product_crawler.pipelines.product_should_be_updated', return_value=True
        )
        mocker.patch(
            'hook_crawlers.product_crawler.pipelines.fetch_product', return_value=True)

        product_creation = mocker.patch(
            'hook_crawlers.product_crawler.pipelines.save_product'
        )
        product_update = mocker.patch(
            'hook_crawlers.product_crawler.pipelines.update_product'
        )
        self.pipeline.process_item(product, spider)
        product_creation.assert_not_called()
        product_update.assert_called_once()
