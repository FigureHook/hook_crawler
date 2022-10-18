from datetime import date, datetime

from hook_crawlers.product_crawler.usecases.release_usecase import (
    ProductReleaseInfoInDB,
    Release,
    ReleaseComparingResult,
    ReleaseUsecase,
)


def assert_change(
    release: Release, db_release: ProductReleaseInfoInDB, status: ReleaseComparingResult
):
    assert status in ReleaseUsecase.get_release_comparing_results(release, db_release)


def test_ignore_case():
    release = Release(
        release_date=date(2222, 2, 1),
    )
    db_release = ProductReleaseInfoInDB(
        id=2,
        product_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        price=100,
        tax_including=False,
        initial_release_date=date(1111, 1, 1),
        adjusted_release_date=date(2222, 2, 1),
        shipped_at=date(2222, 2, 27),
    )
    assert (
        ReleaseComparingResult.IGNORE
        in ReleaseUsecase.get_release_comparing_results(release, db_release)
    )

    db_release.shipped_at = None
    assert (
        ReleaseComparingResult.IGNORE
        in ReleaseUsecase.get_release_comparing_results(release, db_release)
    )


def test_date_change_case():

    release = Release(
        release_date=date(2222, 2, 1),
    )
    db_release = ProductReleaseInfoInDB(
        id=1,
        product_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        price=100,
        tax_including=False,
        initial_release_date=date(1111, 1, 1),
        adjusted_release_date=date(2222, 2, 2),
    )
    assert_change(release, db_release, ReleaseComparingResult.DATE_CHANGE)

    db_release.initial_release_date = None
    db_release.adjusted_release_date = None
    assert_change(release, db_release, ReleaseComparingResult.DATE_CHANGE)

    db_release.initial_release_date = date(111, 1, 1)
    db_release.adjusted_release_date = None
    assert_change(release, db_release, ReleaseComparingResult.DATE_CHANGE)


def test_price_change_case():
    release = Release(
        price=200,
        tax_including=True,
        release_date=date(2222, 2, 1),
    )
    db_release = ProductReleaseInfoInDB(
        id=3,
        product_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        price=100,
        tax_including=False,
        initial_release_date=date(1111, 1, 1),
        adjusted_release_date=date(2222, 2, 2),
    )
    assert_change(release, db_release, ReleaseComparingResult.PRICE_CHANGE)


def test_build_patch_data(release_factory):
    release = release_factory.build()
    release_patch = ReleaseUsecase.build_release_patch_data_by_status(
        incoming_release=release, status_indicator=[ReleaseComparingResult.PRICE_CHANGE]
    )
    assert release.price == release_patch.price
    assert release.tax_including == release_patch.tax_including

    release_patch = ReleaseUsecase.build_release_patch_data_by_status(
        incoming_release=release, status_indicator=[ReleaseComparingResult.DATE_CHANGE]
    )
    assert release.release_date == release_patch.adjusted_release_date
