from logging import Logger
from typing import Optional, Protocol, TypeVar

from figure_hook_client import AuthenticatedClient
from figure_hook_client.api.product import (
    create_product_api_v1_products_post,
    get_products_api_v1_products_get,
    update_product_api_v1_products_product_id_put,
)
from figure_hook_client.models import (
    HTTPValidationError,
    PageProductInDBRich,
    ProductCreate,
    ProductInDBRich,
    ProductUpdate,
    ValidationError,
)
from figure_parser import ProductBase

from .exceptions import HookApiException

ProductType = TypeVar("ProductType", covariant=True)


class ProductRepositoryInterface(Protocol[ProductType]):
    def get_product_by_url(self, *, source_url: str) -> Optional[ProductType]:
        ...

    def create_product(
        self, *, product_base: ProductBase, checksum: str
    ) -> ProductType:
        ...

    def update_product(
        self, *, product_id: int, product_base: ProductBase, checksum: str
    ) -> ProductType:
        ...


class ProductRepository(ProductRepositoryInterface[ProductInDBRich]):
    api_client: AuthenticatedClient
    logger: Logger

    def __init__(self, api_client: AuthenticatedClient) -> None:
        self.api_client = api_client

    def get_product_by_url(self, *, source_url: str) -> Optional[ProductInDBRich]:
        resp = get_products_api_v1_products_get.sync_detailed(
            client=self.api_client, source_url=source_url
        )

        products = resp.parsed
        if not products:
            raise HookApiException(
                status_code=resp.status_code, detail=resp.content, headers=resp.headers
            )

        if isinstance(products, ValidationError):
            raise HookApiException(
                status_code=resp.status_code,
                detail=products.to_dict(),
                headers=resp.headers,
            )

        if isinstance(products, PageProductInDBRich):
            if products.results:
                return products.results[0]

        return None

    def create_product(
        self, *, product_base: ProductBase, checksum: str
    ) -> ProductInDBRich:
        product_create = product_base_to_product_create(
            product_base=product_base, product_checksum=checksum
        )
        resp = create_product_api_v1_products_post.sync_detailed(
            client=self.api_client, json_body=product_create
        )

        created_product = resp.parsed
        if isinstance(created_product, ProductInDBRich):
            return created_product

        elif isinstance(created_product, HTTPValidationError):
            raise HookApiException(
                status_code=resp.status_code,
                detail=created_product.to_dict(),
                headers=resp.headers,
            )

        raise HookApiException(
            status_code=resp.status_code, detail=resp.content, headers=resp.headers
        )

    def update_product(
        self, *, product_id: int, product_base: ProductBase, checksum: str
    ) -> ProductInDBRich:
        product_update = product_base_to_product_update(
            product_base=product_base, product_checksum=checksum
        )
        resp = update_product_api_v1_products_product_id_put.sync_detailed(
            product_id, client=self.api_client, json_body=product_update
        )

        updated_product = resp.parsed
        if isinstance(updated_product, ProductInDBRich):
            return updated_product

        elif isinstance(updated_product, HTTPValidationError):
            raise HookApiException(
                status_code=resp.status_code,
                detail=updated_product.to_dict(),
                headers=resp.headers,
            )

        raise HookApiException(
            status_code=resp.status_code, detail=resp.content, headers=resp.headers
        )


def product_base_to_product_create(
    *, product_base: ProductBase, product_checksum: str
) -> ProductCreate:
    return ProductCreate(
        name=product_base.name,
        rerelease=product_base.rerelease,
        url=product_base.url,
        checksum=product_checksum,
        series=product_base.series,
        category=product_base.category,
        manufacturer=product_base.manufacturer,
        official_images=product_base.images,
        size=product_base.size,
        scale=product_base.scale,
        adult=product_base.adult,
        copyright_=product_base.copyright,
        jan=product_base.jan,
        order_period_start=product_base.order_period.start,
        order_period_end=product_base.order_period.end,
        releaser=product_base.releaser,
        distributer=product_base.distributer,
        sculptors=product_base.sculptors,
        paintworks=product_base.paintworks,
    )


def product_base_to_product_update(
    *, product_base: ProductBase, product_checksum: str
) -> ProductUpdate:
    base_dict = product_base.dict(exclude_none=True)
    base_dict["checksum"] = product_checksum
    return ProductUpdate.from_dict(base_dict)
