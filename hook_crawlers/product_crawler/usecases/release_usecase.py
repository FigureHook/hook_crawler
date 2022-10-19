from datetime import date
from enum import Enum, auto
from typing import List, Set, Union

from figure_hook_client.models import ProductReleaseInfoInDB, ProductReleaseInfoUpdate
from figure_parser import Release

from ..libs.helpers import JapanDatetimeHelper


class ReleaseComparingResult(Enum):

    IGNORE = auto()
    DATE_CHANGE = auto()
    PRICE_CHANGE = auto()


class ReleaseInfoGroupStatus(Enum):
    """
    SAME: No need to do anything.
    NEW_RELEASE: Just add the new releases.
    CHANGE: Need to rebuild the release infos.
    CONFLICT: Data from parser might be unreliable.
    """

    SAME = auto()
    NEW_RELEASE = auto()
    CHANGE = auto()
    CONFLICT = auto()


class ReleaseUsecase:
    @staticmethod
    def get_release_comparing_results(
        in_release: Release, db_release: ProductReleaseInfoInDB
    ) -> List[ReleaseComparingResult]:
        results: List[ReleaseComparingResult] = []
        if db_release.shipped_at:
            results.append(ReleaseComparingResult.IGNORE)

        # Prefer using adjusted_release_date as release-date.
        db_release_date = (
            db_release.adjusted_release_date or db_release.initial_release_date
        )
        if db_release_date == in_release.release_date:
            results.append(ReleaseComparingResult.IGNORE)

        if in_release.release_date:
            # if incoming release-date is less than `today` that means the release has already shipped out.
            # The releass information should not be changed without administrator's confirmation.
            if in_release.release_date <= JapanDatetimeHelper.today():
                results.append(ReleaseComparingResult.IGNORE)

        if in_release.release_date != db_release_date:
            results.append(ReleaseComparingResult.DATE_CHANGE)

        if (
            in_release.price != db_release.price
            or in_release.tax_including != db_release.tax_including
        ):
            results.append(ReleaseComparingResult.PRICE_CHANGE)

        return results or [ReleaseComparingResult.IGNORE]

    @staticmethod
    def get_release_group_comparing_result(
        incoming_releases: List[Release],
        existing_releases: List[ProductReleaseInfoInDB],
    ) -> ReleaseInfoGroupStatus:
        existing_info_dicts = [r.to_dict() for r in existing_releases]
        incoming_dates_set = set(r.release_date for r in incoming_releases)
        existing_dates_set: Set[Union[date, None]] = set(
            r["adjusted_release_date"] or r["initial_release_date"]
            for r in existing_info_dicts
        )

        if len(incoming_dates_set) < len(existing_dates_set):
            return ReleaseInfoGroupStatus.CONFLICT

        if len(incoming_dates_set) > len(existing_dates_set):
            return ReleaseInfoGroupStatus.NEW_RELEASE

        if len(incoming_dates_set) == len(existing_dates_set):
            if incoming_dates_set != existing_dates_set:
                return ReleaseInfoGroupStatus.CHANGE

        return ReleaseInfoGroupStatus.SAME

    @staticmethod
    def build_release_patch_data_by_status(
        incoming_release: Release,
        status_indicator: List[ReleaseComparingResult],
    ) -> ProductReleaseInfoUpdate:
        release_patch = ProductReleaseInfoUpdate()
        for status in status_indicator:
            if status is ReleaseComparingResult.DATE_CHANGE:
                release_patch.adjusted_release_date = incoming_release.release_date
            elif status is ReleaseComparingResult.PRICE_CHANGE:
                release_patch.price = incoming_release.price
                release_patch.tax_including = incoming_release.tax_including
        return release_patch
