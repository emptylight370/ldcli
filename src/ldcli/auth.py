"""登录 / 登出 / 两步验证。

流程参考 docs/API.md：
1. POST /api/v2/login，密码需 MD5 哈希
2. 登录失败次数过多时返回 needCaptcha，需 GET /captcha/login?needCaptcha={...}
   获取验证码图片后带 captcha 字段重试
3. 返回 code=10 表示需要两步验证：携带 login 返回的 token 作为
   Cookie symphony 调用 POST /api/v2/login/2fa，成功后取得正式 token
"""

from __future__ import annotations

import getpass
import hashlib
import tempfile
from pathlib import Path
from typing import Any

from .client import ApiError, Client
from .config import clear_token, save_token


def login(client: Client, *, user_name: str | None, password: str | None) -> str:
    """交互式登录，成功后保存 token 并返回。"""
    if not user_name:
        user_name = input("用户名或邮箱: ").strip()
    if not password:
        password = getpass.getpass("密码: ")
    if not user_name or not password:
        raise ApiError("用户名和密码不能为空")

    payload = _do_login(client, user_name, password, captcha="")

    code = payload.get("code")
    if code == 10:
        # 两步验证：login 返回的 token 仅用于本次 2FA 请求
        print("检测到已开启两步验证，需要输入身份验证器动态口令。")
        twofactor_token = payload.get("token", "")
        auth_code = input("6 位动态口令: ").strip()
        data = client.request_raw(
            "POST",
            "/api/v2/login/2fa",
            json_body={"twofactorAuthCode": auth_code},
            cookie={"symphony": twofactor_token},
        )
        if data.get("code") != 0:
            raise ApiError(f"两步验证失败（code={data.get('code')}）：{data.get('msg') or '无消息'}")
        token = data.get("token")
    elif code == 0:
        token = payload.get("token")
    else:
        raise ApiError(f"登录失败（code={code}）：{payload.get('msg') or '无消息'}")

    if not token:
        raise ApiError("登录响应中未返回 token")
    save_token(token)
    return token


def _do_login(client: Client, user_name: str, password: str, captcha: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "userName": user_name,
        "userPassword": hashlib.md5(password.encode("utf-8")).hexdigest(),
    }
    if captcha:
        body["captcha"] = captcha

    payload = client.request_raw("POST", "/api/v2/login", json_body=body)

    # 登录失败次数过多：needCaptcha 非空时需要验证码后重试
    need_captcha = payload.get("needCaptcha")
    if need_captcha:
        captcha_value = _handle_captcha(client, str(need_captcha))
        return _do_login(client, user_name, password, captcha=captcha_value)
    return payload


def _handle_captcha(client: Client, need_captcha: str) -> str:
    """下载验证码图片到临时文件，提示用户查看并输入。"""
    resp = client._http.get("/captcha/login", params={"needCaptcha": need_captcha})
    resp.raise_for_status()
    suffix = ".png"
    content_type = resp.headers.get("content-type", "")
    if "jpeg" in content_type or "jpg" in content_type:
        suffix = ".jpg"
    if "gif" in content_type:
        suffix = ".gif"
    with tempfile.NamedTemporaryFile(prefix="ldcli-captcha-", suffix=suffix, delete=False) as f:
        f.write(resp.content)
        path = Path(f.name)
    print(f"登录失败次数过多，已下载验证码图片：{path}")
    print("请打开图片查看后输入验证码（该临时文件可手动删除）。")
    return input("验证码: ").strip()


def logout(client: Client) -> None:
    """调用登出接口并清除本地保存的 token。"""
    try:
        client.post("/api/v2/logout")
    except ApiError as e:
        print(f"登出接口返回：{e}")
    if clear_token():
        print("已清除本地保存的 token。")
    else:
        print("本地未保存 token。")
