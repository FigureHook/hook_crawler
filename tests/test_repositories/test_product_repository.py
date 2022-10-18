from hook_crawlers.product_crawler.repositories.product_repository import (
    product_base_to_product_create,
    product_base_to_product_update,
)


def test_product_base_to_product_create(product_base_factory):
    product = product_base_factory.build()
    product_base_to_product_create(product_base=product, product_checksum="123")


def test_product_base_to_product_update(product_base_factory):
    product = product_base_factory.build()
    product_base_to_product_update(product_base=product, product_checksum="123")
