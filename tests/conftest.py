from figure_parser import OrderPeriod, ProductBase, Release
from pydantic_factories import ModelFactory
from pydantic_factories.plugins.pytest_plugin import register_fixture


@register_fixture
class ProductBaseFactory(ModelFactory):
    """A product-base factory."""

    OrderPeriod.__pre_root_validators__ = []
    "Disable the validator."
    __model__ = ProductBase


@register_fixture
class ReleaseFactory(ModelFactory):
    """A release factory."""

    __model__ = Release
