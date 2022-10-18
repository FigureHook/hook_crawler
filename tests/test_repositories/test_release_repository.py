from hook_crawlers.product_crawler.repositories.release_repository import (
    release_to_release_create,
)


def test_build_release_create_by_release(release_factory):
    release = release_factory.build()
    release_to_release_create(release)
