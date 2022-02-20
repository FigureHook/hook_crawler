from typing import Literal


def valid_year(
    year,
    top: int,
    bottom: int,
    fallback_flag: Literal['top', 'bottom']
) -> int:
    is_int = type(year) is int

    def _fallback(year, flag):
        if flag == 'top':
            return top
        if flag == 'bottom':
            return bottom
        return year

    if is_int:
        is_in_range = bottom <= year <= top
        if not is_in_range:
            year = _fallback(year, fallback_flag)

    if not is_int:
        try:
            year = int(year)
        except:
            year = _fallback(year, fallback_flag)

    return year
