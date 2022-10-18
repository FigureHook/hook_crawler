import hashlib
from typing import Sequence

from figure_parser import OrderPeriod
from itemadapter import ItemAdapter


def _get_order_period_timestamp_sum(order_period: OrderPeriod):
    start = order_period.start.timestamp() if order_period.start else 0
    end = order_period.end.timestamp() if order_period.end else 0
    return int(sum((start, end)))


def generate_item_checksum(item) -> str:
    item = ItemAdapter(item)
    md5 = hashlib.md5()
    update_strategy = {
        str: lambda v: md5.update(v.encode("utf-8")),
        int: lambda v: md5.update(v.to_bytes(32, "big")),
        bool: lambda v: md5.update(str(v).encode("utf-8")),
    }

    for key in item.keys():
        value = item[key]
        if type(value) in update_strategy:
            update_strategy[type(value)](value)
        elif isinstance(value, Sequence):
            if all(type(n) in update_strategy for n in value):
                for n in value:
                    update_strategy[type(n)](n)
        elif isinstance(value, OrderPeriod):
            update_strategy[int](_get_order_period_timestamp_sum(value))

    return md5.hexdigest()
