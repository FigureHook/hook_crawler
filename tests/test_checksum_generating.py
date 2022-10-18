from hook_crawlers.product_crawler.libs.checksums import generate_item_checksum


def test_product_checksum_generating(product_base_factory):
    mock_product = product_base_factory.build()
    prev_checksum = generate_item_checksum(mock_product)
    mock_product.size = 280
    current_checksum = generate_item_checksum(mock_product)

    assert prev_checksum != current_checksum
