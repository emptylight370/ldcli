"""ld246.com 社区 API 客户端。

遵循 docs/API.md 公共约定：
- 自定义 User-Agent（ldcli/{ver}），避免被流量监控拦截
- Authorization: token {token} 鉴权
- 校验 HTTP 状态码（401 需登录 / 403 权限不足）与响应体 code 字段
- 客户端限流，避免超过 120 次/分钟
"""

from __future__ import annotations

import json as jsonlib
import time
from typing import Any

import httpx

from ._version import __version__

BASE_URL = "https://ld246.com"
USER_AGENT = f"ldcli/{__version__}"

# 每个 IP 每分钟最多 120 次，客户端保守限制为 100 次/分钟
_MIN_INTERVAL = 60.0 / 100.0


class ApiError(Exception):
    """API 调用失败（非零 code、HTTP 错误或网络异常）。"""


class Client:
    """封装对社区 REST API 的访问。"""
    def __init__(self, token: str | None = None) -> None:
        self.token = token
        headers = {"User-Agent": USER_AGENT}
        if token:
            headers["Authorization"] = f"token {token}"
        self._http = httpx.Client(base_url=BASE_URL, headers=headers, timeout=15.0)
        self._last_request_at: float = 0.0

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        cookie: dict[str, str] | None = None,
    ) -> Any:
        """发起请求并返回响应体中的 data 字段。

        登录等接口的响应结构不同（token 在顶层），请改用 request_raw。
        """
        payload = self.request_raw(
            method,
            path,
            params=params,
            json_body=json_body,
            extra_headers=extra_headers,
            cookie=cookie,
        )
        if payload.get("code") not in (0, None):
            raise ApiError(f"API 返回错误（code={payload.get('code')}）：{payload.get('msg') or '无消息'}")
        return payload.get("data")

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        cookie: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """发起请求并返回完整 JSON 响应体。"""
        self._throttle()
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            resp = self._http.request(
                method,
                path,
                params=clean_params,
                json=json_body,
                headers=extra_headers,
                cookies=cookie,
            )
        except httpx.HTTPError as e:
            raise ApiError(f"网络请求失败：{e}") from e

        if resp.status_code == 401:
            raise ApiError(
                "需要登录（401）：请先执行 ldcli login <token> 保存 API Token"
                "（在 ld246.com 设置-账号 页面获取），或通过 --token/LDCLI_TOKEN 提供"
            )
        if resp.status_code == 403:
            raise ApiError("权限不足（403）：当前账号无权执行该操作")
        if resp.status_code >= 400:
            raise ApiError(f"HTTP {resp.status_code}：{resp.text[:200]}")

        try:
            payload = resp.json()
        except jsonlib.JSONDecodeError as e:
            raise ApiError(f"响应不是合法 JSON：{resp.text[:200]}") from e
        if not isinstance(payload, dict):
            raise ApiError(f"响应结构异常：{str(payload)[:200]}")
        return payload

    def set_token(self, token: str | None) -> None:
        """更新鉴权 Token（用于 login 命令验证新 Token）。"""
        self.token = token
        if token:
            self._http.headers["Authorization"] = f"token {token}"
        else:
            self._http.headers.pop("Authorization", None)

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def _throttle(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if self._last_request_at > 0 and elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
