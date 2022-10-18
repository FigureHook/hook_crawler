from typing import Any, Mapping


class ApiException(Exception):
    def __init__(self, status_code: int, detail: Any, **kwargs) -> None:
        super().__init__({"status_code": status_code, "detail": detail, **kwargs})


class HookApiException(ApiException):
    def __init__(
        self, status_code: int, detail: Any, headers: Mapping[str, Any]
    ) -> None:
        ext_info = {"request_id": headers.get("X-Request-ID")}
        super().__init__(status_code, detail, **ext_info)
