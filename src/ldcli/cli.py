"""命令行入口：基于 argparse 的子命令树。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from ._version import __version__
from .auth import login as auth_login
from .auth import logout as auth_logout
from .client import ApiError, Client
from .config import TOKEN_ENV, load_token
from .output import emit, html_to_text, print_articles_brief

NOTIFY_TYPES = ("commented", "comment2ed", "reply", "at", "following", "point", "broadcast", "wallet", "sys-announce")
NOTIFY_READABLE = ("commented", "comment2ed", "reply", "at", "following")
SORTS = ("time", "hot", "good", "reply", "perfect")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ldcli",
        description="ld246.com 社区命令行客户端（API 文档见 docs/API.md）",
    )
    parser.add_argument("--version", action="version", version=f"ldcli {__version__}")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 而非人类可读格式")
    parser.add_argument("--token", help=f"API Token（默认依次读取参数、环境变量 {TOKEN_ENV}、配置文件）")
    parser.set_defaults(func=None)
    parser.set_defaults(as_json=False)

    sub = parser.add_subparsers(title="子命令", metavar="<command>")

    # ---- login / logout / whoami ----
    p = sub.add_parser("login", help="录入 API Token 并保存（Token 在 ld246.com 设置-账号 页面获取）")
    p.add_argument("token", nargs="?", help="API Token（省略则交互输入）")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("logout", help="登出并清除本地 token")
    p.set_defaults(func=cmd_logout)

    p = sub.add_parser("whoami", help="查看当前登录用户详情")
    p.set_defaults(func=cmd_whoami, table_key="users")

    # ---- article ----
    p = sub.add_parser("article", help="帖子相关操作")
    article_sub = p.add_subparsers(title="article 子命令", metavar="<action>", required=True)

    p = article_sub.add_parser("list", help="最新帖子列表")
    p.add_argument("-s", "--sort", choices=SORTS, default="time", help="排序方式（默认 time）")
    p.add_argument("-p", "--page", type=int, default=1, help="页号（默认 1，页大小固定 20）")
    p.add_argument("--full", action="store_true", help="输出完整表格视图（默认简洁视图）")
    p.set_defaults(func=cmd_article_list, table_key="articles")

    p = article_sub.add_parser("domain", help="领域帖子列表")
    p.add_argument("uri", help="领域 URI，如 Java")
    p.add_argument("-p", "--page", type=int, default=1)
    p.add_argument("--full", action="store_true", help="输出完整表格视图（默认简洁视图）")
    p.set_defaults(func=cmd_article_domain, table_key="articles")

    p = article_sub.add_parser("tag", help="标签帖子列表")
    p.add_argument("uri", help="标签 URI，如 Java")
    p.add_argument("-s", "--sort", choices=SORTS, default="time")
    p.add_argument("-p", "--page", type=int, default=1)
    p.add_argument("--full", action="store_true", help="输出完整表格视图（默认简洁视图）")
    p.set_defaults(func=cmd_article_tag, table_key="articles")

    p = article_sub.add_parser("show", help="帖子详情（含回帖）")
    p.add_argument("id", help="帖子 ID")
    p.add_argument("-p", "--page", type=int, default=1, help="回帖页号")
    p.set_defaults(func=cmd_article_show)

    p = article_sub.add_parser("post", help="发布帖子")
    p.add_argument("--title", required=True, help="帖子标题")
    p.add_argument("--tags", required=True, help="标签，英文逗号分隔")
    p.add_argument("--content", help="正文内容（与 --file 二选一，均省略时交互输入）")
    p.add_argument("--file", help="从文件读取正文（'-' 表示 stdin）")
    p.add_argument("--reward-content", help="打赏区内容")
    p.add_argument("--reward-point", type=int, help="打赏积分")
    p.set_defaults(func=cmd_article_post)

    p = article_sub.add_parser("update", help="更新帖子")
    p.add_argument("id", help="帖子 ID")
    p.add_argument("--title", help="新标题")
    p.add_argument("--tags", help="新标签，英文逗号分隔")
    p.add_argument("--content", help="新正文（与 --file 二选一）")
    p.add_argument("--file", help="从文件读取新正文（'-' 表示 stdin）")
    p.add_argument("--reward-content", help="打赏区内容")
    p.add_argument("--reward-point", type=int, help="打赏积分")
    p.set_defaults(func=cmd_article_update)

    # ---- comment ----
    p = sub.add_parser("comment", help="回帖相关操作")
    comment_sub = p.add_subparsers(title="comment 子命令", metavar="<action>", required=True)

    p = comment_sub.add_parser("post", help="发布回帖")
    p.add_argument("--article", required=True, help="帖子 ID")
    p.add_argument("--content", help="回帖内容（与 --file 二选一，均省略时交互输入）")
    p.add_argument("--file", help="从文件读取内容（'-' 表示 stdin）")
    p.add_argument("--reply", help="被回复的回帖 ID（楼中楼回复时使用）")
    p.set_defaults(func=cmd_comment_post)

    # ---- domain ----
    p = sub.add_parser("domain", help="领域相关操作")
    domain_sub = p.add_subparsers(title="domain 子命令", metavar="<action>", required=True)

    p = domain_sub.add_parser("list", help="领域列表")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_domain_list, table_key="domains")

    p = domain_sub.add_parser("show", help="领域详情")
    p.add_argument("uri", help="领域 URI")
    p.set_defaults(func=cmd_domain_show)

    # ---- tag ----
    p = sub.add_parser("tag", help="标签相关操作")
    tag_sub = p.add_subparsers(title="tag 子命令", metavar="<action>", required=True)

    p = tag_sub.add_parser("list", help="标签列表")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_tag_list, table_key="tags")

    p = tag_sub.add_parser("show", help="标签详情")
    p.add_argument("uri", help="标签 URI")
    p.set_defaults(func=cmd_tag_show)

    # ---- user ----
    p = sub.add_parser("user", help="用户相关操作")
    user_sub = p.add_subparsers(title="user 子命令", metavar="<action>", required=True)

    p = user_sub.add_parser("show", help="根据用户名获取用户详情")
    p.add_argument("name", help="用户名")
    p.set_defaults(func=cmd_user_show, table_key="users")

    p = user_sub.add_parser("no", help="根据用户序号获取用户详情")
    p.add_argument("user_no", type=int, help="用户序号")
    p.set_defaults(func=cmd_user_no, table_key="users")

    p = user_sub.add_parser("articles", help="用户帖子列表")
    p.add_argument("name")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_user_articles, table_key="articles")

    p = user_sub.add_parser("comments", help="用户回帖列表")
    p.add_argument("name")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_user_comments, table_key="comments")

    p = user_sub.add_parser("events", help="用户近期动态")
    p.add_argument("name")
    p.add_argument("--size", type=int, default=16, help="条数（1-64，默认 16）")
    p.set_defaults(func=cmd_user_events)

    p = user_sub.add_parser("watching", help="用户关注帖子列表")
    p.add_argument("name")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_user_watching, table_key="articles")

    p = user_sub.add_parser("following", help="用户关注列表")
    p.add_argument("name")
    p.add_argument("--type", choices=("users", "tags", "articles"), required=True, help="关注对象类型")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_user_following)

    p = user_sub.add_parser("followers", help="用户关注者列表")
    p.add_argument("name")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_user_followers, table_key="users")

    # ---- notify ----
    p = sub.add_parser("notify", help="通知相关操作")
    notify_sub = p.add_subparsers(title="notify 子命令", metavar="<action>", required=True)

    p = notify_sub.add_parser("unread", help="未读消息计数")
    p.set_defaults(func=cmd_notify_unread)

    p = notify_sub.add_parser("list", help="消息列表")
    p.add_argument("type", choices=NOTIFY_TYPES, help="消息类型")
    p.add_argument("-p", "--page", type=int, default=1)
    p.set_defaults(func=cmd_notify_list, table_key="notifications")

    p = notify_sub.add_parser("read", help="标记消息列表为已读")
    p.add_argument("type", choices=NOTIFY_READABLE, help="消息类型")
    p.set_defaults(func=cmd_notify_read)

    # ---- top ----
    p = sub.add_parser("top", help="榜单")
    top_sub = p.add_subparsers(title="top 子命令", metavar="<action>", required=True)

    p = top_sub.add_parser("newbies", help="新注册用户列表")
    p.set_defaults(func=cmd_top_newbies, table_key="users")

    p = top_sub.add_parser("followers", help="粉丝榜")
    p.set_defaults(func=cmd_top_followers, table_key="users")

    # ---- system ----
    p = sub.add_parser("system", help="系统信息")
    system_sub = p.add_subparsers(title="system 子命令", metavar="<action>", required=True)

    p = system_sub.add_parser("time", help="获取系统当前时间")
    p.set_defaults(func=cmd_system_time)

    return parser


# ---- 入口分发 ----


def run(args: argparse.Namespace) -> int:
    if getattr(args, "func", None) is None:
        args.parser.print_help()
        return 0

    as_json = getattr(args, "as_json", False) or args.json
    table_key = getattr(args, "table_key", None)

    token = args.token or load_token()
    with Client(token=token) as client:
        data = args.func(client, args)

    if data is None:
        return 0
    emit(data, as_json=as_json, table_key=table_key)
    return 0


def main(argv: list[str] | None = None) -> int:
    # 强制 UTF-8 输出，避免 Windows 管道/重定向下中文乱码
    for stream in (sys.stdout, sys.stderr):
        enc = (stream.encoding or "").lower().replace("-", "")
        if enc and enc != "utf8":
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass
    parser = build_parser()
    normalized = _normalize_global_args(argv if argv is not None else sys.argv[1:])
    args = parser.parse_args(normalized)
    args.parser = parser
    args.as_json = args.json
    try:
        return run(args)
    except ApiError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        return 130


# ---- 各子命令实现（返回 API data 供统一输出）----


def _normalize_global_args(argv: list[str]) -> list[str]:
    """把全局参数（--json / --token）提前到子命令之前，允许其出现在任意位置。"""
    global_args: list[str] = []
    rest: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            global_args.append(arg)
            i += 1
        elif arg == "--token":
            global_args.extend(argv[i:i + 2])
            i += 2
        else:
            rest.append(arg)
            i += 1
    return global_args + rest


def cmd_login(client: Client, args: argparse.Namespace) -> None:
    # 优先取位置参数，其次全局 --token
    auth_login(client, args.token or client.token)
    print("API Token 已验证并保存到配置文件。")
    return None


def cmd_logout(client: Client, args: argparse.Namespace) -> None:
    auth_logout()
    return None


def cmd_whoami(client: Client, args: argparse.Namespace) -> Any:
    return client.get("/api/v2/user")


def _latest_path(sort: str) -> str:
    return "/api/v2/articles/latest" if sort == "time" else f"/api/v2/articles/latest/{sort}"


def _emit_articles(data: Any, args: argparse.Namespace) -> None:
    """帖子列表输出：--json 原始 JSON；--full 完整表格；默认简洁视图。"""
    if args.json:
        emit(data, as_json=True)
        return
    if isinstance(data, dict):
        rows = data.get("articles") or []
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    if getattr(args, "full", False):
        emit(rows, as_json=False, table_key="articles")
    else:
        print_articles_brief(rows)


def cmd_article_list(client: Client, args: argparse.Namespace) -> Any:
    data = client.get(_latest_path(args.sort), params={"p": args.page})
    _emit_articles(data, args)
    return None


def cmd_article_domain(client: Client, args: argparse.Namespace) -> Any:
    data = client.get(f"/api/v2/articles/domain/{args.uri}", params={"p": args.page})
    _emit_articles(data, args)
    return None


def cmd_article_tag(client: Client, args: argparse.Namespace) -> Any:
    path = f"/api/v2/articles/tag/{args.uri}"
    if args.sort != "time":
        path += f"/{args.sort}"
    data = client.get(path, params={"p": args.page})
    _emit_articles(data, args)
    return None


def cmd_article_show(client: Client, args: argparse.Namespace) -> Any:
    data = client.get(f"/api/v2/article/{args.id}", params={"p": args.page})
    if not args.json and isinstance(data, dict):
        _render_article_detail(data, page=args.page)
        return None
    return data


def _render_article_detail(data: dict[str, Any], page: int = 1) -> None:
    article = data.get("article") or {}
    print(f"标题: {article.get('articleTitle', '')}")
    print(f"作者: {article.get('articleAuthorName', article.get('userName', ''))}")
    print(f"ID: {article.get('oId', article.get('articleId', ''))}")
    print(f"标签: {article.get('articleTags', '')}")
    print(f"浏览: {article.get('articleViewCount', '')}  回帖: {article.get('articleCommentCount', '')}")
    print("-" * 60)
    print(html_to_text(article.get("articleContent")))
    comments = article.get("articleComments") or data.get("comments") or []
    if comments:
        print("-" * 60)
        print(f"回帖（本页 {len(comments)} 条）:")
        print()
        for c in comments:
            author = c.get("commentAuthorName", c.get("userName", ""))
            time_ago = c.get("timeAgo", "")
            suffix = f" · {time_ago}" if time_ago else ""
            print(f"[{c.get('oId', '')}] {author}{suffix}:")
            content = html_to_text(c.get("commentContent"))
            for line in content.split("\n"):
                print(f"    {line}")
            print()
    # 回帖分页提示
    pagination = data.get("pagination") or {}
    page_count = pagination.get("paginationPageCount") or 1
    if int(page_count) > 1:
        print(f"回帖共 {page_count} 页，当前第 {page} 页，可用 -p 翻页。")


def _read_content(args: argparse.Namespace) -> str:
    if getattr(args, "file", None):
        if args.file == "-":
            return sys.stdin.read()
        return Path(args.file).read_text(encoding="utf-8")
    if args.content is not None:
        return args.content
    print("请输入内容，单独一行输入 . 结束：")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines)


def cmd_article_post(client: Client, args: argparse.Namespace) -> Any:
    body: dict[str, Any] = {
        "articleTitle": args.title,
        "articleTags": args.tags,
        "articleContent": _read_content(args),
    }
    if args.reward_content is not None:
        body["articleRewardContent"] = args.reward_content
    if args.reward_point is not None:
        body["articleRewardPoint"] = args.reward_point
    result = client.post("/api/v2/article", json_body=body)
    if not args.json:
        print("帖子发布成功。")
    return result


def cmd_article_update(client: Client, args: argparse.Namespace) -> Any:
    # PUT 需要传入 articleType，通过“获取帖子详情用于更新”接口取得
    current = client.get(f"/api/v2/article/update/{args.id}")
    body: dict[str, Any] = {}
    if isinstance(current, dict):
        for key in (
            "articleTitle",
            "articleTags",
            "articleContent",
            "articleType",
            "articleRewardContent",
            "articleRewardPoint"
        ):
            if key in current:
                body[key] = current[key]
    if args.title is not None:
        body["articleTitle"] = args.title
    if args.tags is not None:
        body["articleTags"] = args.tags
    if args.content is not None or args.file is not None:
        body["articleContent"] = _read_content(args)
    if args.reward_content is not None:
        body["articleRewardContent"] = args.reward_content
    if args.reward_point is not None:
        body["articleRewardPoint"] = args.reward_point
    result = client.put(f"/api/v2/article/{args.id}", json_body=body)
    if not args.json:
        print("帖子更新成功。")
    return result


def cmd_comment_post(client: Client, args: argparse.Namespace) -> Any:
    body: dict[str, Any] = {
        "articleId": args.article,
        "commentContent": _read_content(args),
    }
    if args.reply:
        body["commentOriginalCommentId"] = args.reply
    result = client.post("/api/v2/comment", json_body=body)
    if not args.json:
        print("回帖发布成功。")
    return result


def cmd_domain_list(client: Client, args: argparse.Namespace) -> Any:
    return client.get("/api/v2/domains", params={"p": args.page})


def cmd_domain_show(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/domain/{args.uri}")


def cmd_tag_list(client: Client, args: argparse.Namespace) -> Any:
    return client.get("/api/v2/tags", params={"p": args.page})


def cmd_tag_show(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/tag/{args.uri}")


def cmd_user_show(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/user/{args.name}")


def cmd_user_no(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/user/n/{args.user_no}")


def cmd_user_articles(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/user/{args.name}/articles", params={"p": args.page})


def cmd_user_comments(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/user/{args.name}/comments", params={"p": args.page})


def cmd_user_events(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/user/{args.name}/events", params={"size": args.size})


def cmd_user_watching(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/user/{args.name}/watching/articles", params={"p": args.page})


def cmd_user_following(client: Client, args: argparse.Namespace) -> Any:
    paths = {
        "users": "/following/users",
        "tags": "/following/tags",
        "articles": "/following/articles",
    }
    return client.get(f"/api/v2/user/{args.name}{paths[args.type]}", params={"p": args.page})


def cmd_user_followers(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/user/{args.name}/followers", params={"p": args.page})


def cmd_notify_unread(client: Client, args: argparse.Namespace) -> Any:
    return client.get("/api/v2/notifications/unread/count")


def cmd_notify_list(client: Client, args: argparse.Namespace) -> Any:
    return client.get(f"/api/v2/notifications/{args.type}", params={"p": args.page})


def cmd_notify_read(client: Client, args: argparse.Namespace) -> Any:
    result = client.get(f"/api/v2/notifications/make-read/{args.type}")
    if not args.json:
        print(f"已将 {args.type} 类型消息标记为已读。")
    return result


def cmd_top_newbies(client: Client, args: argparse.Namespace) -> Any:
    return client.get("/api/v2/tops/users/newbies")


def cmd_top_followers(client: Client, args: argparse.Namespace) -> Any:
    return client.get("/api/v2/tops/users/followers")


def cmd_system_time(client: Client, args: argparse.Namespace) -> Any:
    return client.get("/api/v2/system/time")
