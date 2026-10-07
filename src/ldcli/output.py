"""输出格式化：默认人类可读格式，支持 --json 输出原始 JSON。"""

from __future__ import annotations

import json
import sys
from typing import Any

# 各表头键名 -> 显示标题（顺序即列顺序）
TABLE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "articles": [
        ("oId", "ID"),
        ("articleTitle", "标题"),
        ("articleAuthorName", "作者"),
        ("articleCommentCount", "回帖"),
        ("articleViewCount", "浏览"),
    ],
    "domains": [
        ("domainURI", "URI"),
        ("domainTitle", "标题"),
        ("domainDescription", "描述"),
    ],
    "tags": [
        ("tagURI", "URI"),
        ("tagTitle", "标题"),
        ("tagDescription", "描述"),
    ],
    "users": [
        ("userName", "用户名"),
        ("userNo", "序号"),
        ("userTag", "签名"),
    ],
    "notifications": [
        ("id", "ID"),
        ("dataType", "类型"),
        ("dataId", "数据ID"),
        ("description", "内容"),
        ("createTime", "时间"),
    ],
    "comments": [
        ("oId", "ID"),
        ("commentAuthorName", "作者"),
        ("commentContent", "内容"),
        ("commentCreateTime", "时间"),
    ],
}


def emit(data: Any, *, as_json: bool, table_key: str | None = None) -> None:
    """按格式输出数据：JSON 或人类可读。"""
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return
    print_pretty(data, table_key=table_key)


def print_pretty(data: Any, *, table_key: str | None = None) -> None:
    if data is None:
        print("(无数据)")
        return
    if isinstance(data, list):
        if table_key and table_key in TABLE_COLUMNS:
            _print_table(data, TABLE_COLUMNS[table_key])
        else:
            for item in data:
                _print_kv(item)
                print("-" * 40)
        return
    _print_kv(data)


def print_articles_brief(rows: list[Any]) -> None:
    """帖子列表简洁视图：一行标题 + 一行摘要，条目间以空行分隔。"""
    if not rows:
        print("(空列表)")
        return
    for i, row in enumerate(rows, 1):
        title = _plain(_get(row, "articleTitle"))
        perfect = str(_get(row, "articlePerfect") or "0")
        if perfect not in ("0", "", "None"):
            title = f"[精] {title}"
        print(f"{i:>3}. {title}")

        meta: list[str] = []
        author = _plain(_get(row, "articleAuthorName"))
        if author:
            meta.append(author)
        tags = _plain(_get(row, "articleTags"))
        if tags:
            meta.append(tags)
        comments = _get(row, "articleCommentCount")
        if str(comments or "0") not in ("0", "", "None"):
            meta.append(f"回帖 {comments}")
        time_ago = _get(row, "timeAgo")
        if time_ago:
            meta.append(str(time_ago))
        line = " · ".join(meta)
        oid = _get(row, "oId") or _get(row, "articleId")
        if oid:
            line = f"{line}  ({oid})" if line else f"(ID {oid})"
        if line:
            print(f"     {line}")
        print()


def plain_text(value: Any) -> str:
    """将 markdown/HTML 片段压成单行纯文本。"""
    return _plain(value)


def html_to_text(value: Any) -> str:
    """将 HTML 片段转为多行纯文本，保留段落换行。"""
    import html as html_lib
    import re

    text = "" if value is None else str(value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"(?i)<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _print_table(rows: list[Any], columns: list[tuple[str, str]]) -> None:
    if not rows:
        print("(空列表)")
        return
    rendered: list[list[str]] = []
    for row in rows:
        cells = []
        for key, _ in columns:
            value = _get(row, key)
            text = _plain(value)
            # 单元格过长时截断，避免破坏对齐
            if len(text) > 40:
                text = text[:39] + "…"
            cells.append(text.replace("\n", " "))
        rendered.append(cells)

    headers = [title for _, title in columns]
    widths = [max(len(headers[i]), *(len(r[i]) for r in rendered)) for i in range(len(columns))]

    def fmt(cells: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for row in rendered:
        print(fmt(row))


def _print_kv(data: Any, indent: int = 0) -> None:
    pad = "  " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{pad}{key}:")
                _print_kv(value, indent + 1)
            else:
                print(f"{pad}{key}: {_plain(value)}")
    elif isinstance(data, list):
        for item in data:
            _print_kv(item, indent)
    else:
        print(f"{pad}{_plain(data)}")


def _get(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key, "")
    return getattr(row, key, "")


def _plain(value: Any) -> str:
    """将 markdown/HTML 片段压成单行纯文本摘要。"""
    text = "" if value is None else str(value)
    for tag in ("<br>", "</p>", "<p>", "\n", "\r"):
        text = text.replace(tag, " ")
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


def markdown_block(content: Any) -> None:
    """输出多行 markdown 内容（帖子正文、回帖内容）。"""
    if content is None:
        content = ""
    if not sys.stdout.isatty():
        print(content)
        return
    print(content)
