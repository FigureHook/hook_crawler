from typing import List, Protocol, TypeVar

from figure_hook_client import AuthenticatedClient
from figure_hook_client.api.product import (
    create_product_release_info_api_v1_products_product_id_release_infos_post,
    get_product_release_infos_api_v1_products_product_id_release_infos_get,
    patch_product_release_info_api_v1_products_product_id_release_infos_release_id_patch,
)
from figure_hook_client.models import (
    HTTPValidationError,
    ProductReleaseInfoCreate,
    ProductReleaseInfoInDB,
    ProductReleaseInfoUpdate,
)
from figure_parser import Release

from .exceptions import HookApiException

ReleaseType = TypeVar("ReleaseType")
ReleaseUpdateType = TypeVar("ReleaseUpdateType", contravariant=True)


class ReleaseRepositoryInterface(Protocol[ReleaseType, ReleaseUpdateType]):
    def get_releases_by_product_id(self, *, product_id: int) -> List[ReleaseType]:
        ...

    def create_release_own_by_product(
        self, *, product_id: int, release: Release
    ) -> ReleaseType:
        ...

    def update_release(
        self, *, product_id: int, release_id: int, release: ReleaseUpdateType
    ) -> ReleaseType:
        ...


class ReleaseRepository(
    ReleaseRepositoryInterface[ProductReleaseInfoInDB, ProductReleaseInfoUpdate]
):
    api_client: AuthenticatedClient

    def __init__(self, api_client: AuthenticatedClient) -> None:
        self.api_client = api_client

    def get_releases_by_product_id(
        self, *, product_id: int
    ) -> List[ProductReleaseInfoInDB]:
        resp = get_product_release_infos_api_v1_products_product_id_release_infos_get.sync_detailed(
            product_id=product_id,
            client=self.api_client,
        )

        releases = resp.parsed
        if type(releases) is list:
            return releases

        if isinstance(releases, HTTPValidationError):
            raise HookApiException(
                status_code=resp.status_code,
                detail=releases.to_dict(),
                headers=resp.headers,
            )

        raise HookApiException(
            status_code=resp.status_code, detail=resp.content, headers=resp.headers
        )

    def create_release_own_by_product(
        self, *, product_id: int, release: Release
    ) -> ProductReleaseInfoInDB:
        release_create = release_to_release_create(release)
        resp = create_product_release_info_api_v1_products_product_id_release_infos_post.sync_detailed(
            product_id=product_id, client=self.api_client, json_body=release_create
        )

        created_release = resp.parsed
        if isinstance(created_release, ProductReleaseInfoInDB):
            return created_release

        if isinstance(created_release, HTTPValidationError):
            raise HookApiException(
                status_code=resp.status_code,
                detail=created_release.to_dict(),
                headers=resp.headers,
            )

        raise HookApiException(
            status_code=resp.status_code, detail=resp.content, headers=resp.headers
        )

    def update_release(
        self, *, product_id: int, release_id: int, release: ProductReleaseInfoUpdate
    ) -> ProductReleaseInfoInDB:
        resp = patch_product_release_info_api_v1_products_product_id_release_infos_release_id_patch.sync_detailed(
            client=self.api_client,
            product_id=product_id,
            release_id=release_id,
            json_body=release,
        )
        updated_release = resp.parsed
        if isinstance(updated_release, ProductReleaseInfoInDB):
            return updated_release

        if isinstance(updated_release, HTTPValidationError):
            raise HookApiException(
                status_code=resp.status_code,
                detail=updated_release.to_dict(),
                headers=resp.headers,
            )

        raise HookApiException(
            status_code=resp.status_code, detail=resp.content, headers=resp.headers
        )


def release_to_release_create(release: Release) -> ProductReleaseInfoCreate:
    return ProductReleaseInfoCreate(
        price=release.price,
        tax_including=release.tax_including,
        initial_release_date=release.release_date,
        announced_at=release.announced_at,
    )
