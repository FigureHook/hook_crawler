from hook_crawlers.product_crawler.pipelines import (
    fill_announced_date,
    get_last_release,
    is_announcement_spider,
)


def test_get_last_release(product_base_factory):
    mock_product = product_base_factory.build()
    assert get_last_release(mock_product)
    mock_product.releases.pop()
    assert not get_last_release(mock_product)


def test_is_announcement_spider():
    class Spider:
        is_announcement_spider = True

    spider = Spider()
    assert is_announcement_spider(spider)
    spider.is_announcement_spider = False
    assert not is_announcement_spider(spider)


def test_filling_announced_date(product_base_factory):
    mock_product = product_base_factory.build()
    product = fill_announced_date(mock_product)
    releases = product.releases
    assert releases
    assert releases[-1].announced_at is not None
