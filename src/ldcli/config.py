"""配置管理：token 持久化到 ~/.ldcli.toml。"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

CONFIG_FILE = Path.home() / ".ldcli.toml"

TOKEN_ENV = "LDCLI_TOKEN"


def load_token() -> str | None:
    """按优先级读取 token：环境变量 > 配置文件。"""
    env_token = os.environ.get(TOKEN_ENV, "").strip()
    if env_token:
        return env_token
    data = _read_config()
    auth = data.get("auth") or {}
    token = auth.get("token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def save_token(token: str) -> None:
    data = _read_config()
    data.setdefault("auth", {})["token"] = token
    _write_config(data)


def clear_token() -> bool:
    """清除已保存的 token，返回之前是否存在 token。"""
    data = _read_config()
    auth = data.get("auth") or {}
    existed = bool(auth.get("token"))
    if existed:
        auth.pop("token", None)
        if auth:
            data["auth"] = auth
        else:
            data.pop("auth", None)
        _write_config(data)
    return existed


def _read_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"配置文件 {CONFIG_FILE} 解析失败：{e}") from e


def _write_config(data: dict) -> None:
    lines: list[str] = []
    auth = data.get("auth") or {}
    if auth:
        lines.append("[auth]")
        for key, value in auth.items():
            lines.append(f'{key} = "{value}"')
        lines.append("")
    CONFIG_FILE.write_text("\n".join(lines), encoding="utf-8")
