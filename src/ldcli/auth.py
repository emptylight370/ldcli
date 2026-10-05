"""API Token 录入 / 登出。

鉴权方式遵循 docs/API.md：Authorization: token {API Token}，
API Token 在 ld246.com 的 设置-账号 页面获取。
"""

from __future__ import annotations

from .client import ApiError, Client
from .config import CONFIG_FILE, clear_token, save_token


def login(client: Client, token: str | None) -> str:
    """录入 API Token：先调用 /api/v2/user 验证有效性，通过后保存到配置文件。"""
    token = (token or "").strip()
    if not token:
        token = input("请输入 API Token（在 ld246.com 设置-账号 页面获取）: ").strip()
    if not token:
        raise ApiError("Token 不能为空")

    previous = client.token
    client.set_token(token)
    try:
        client.get("/api/v2/user")
    except ApiError as e:
        client.set_token(previous)
        raise ApiError(f"Token 验证失败，未保存：{e}") from e
    save_token(token)
    return token


def logout() -> None:
    """清除本地保存的 API Token。"""
    if clear_token():
        print(f"已从 {CONFIG_FILE} 清除 API Token。")
    else:
        print("本地未保存 API Token。")
