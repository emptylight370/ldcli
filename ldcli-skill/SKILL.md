---
name: ldcli-skill
description: 使用 ldcli 命令行工具访问 ld246.com 论坛（黑客派/Symphony 社区）的只读查询。此 skill 应在用户要求浏览帖子列表、查看帖子详情与回帖、查询领域/标签/用户信息、查看或处理通知、查看榜单，或提到 ldcli/论坛命令行时使用。注意：发帖、回帖等写操作为部分可用状态，不建议使用；需要发布内容时提示用户手动复制粘贴到论坛网页端。
---

# ldcli — ld246.com 论坛命令行

## 概述

`ldcli` 是 ld246.com 社区的命令行客户端，基于 ld246.com 的 API v2 实现。支持帖子（浏览/发布/更新）、回帖、领域、标签、用户、通知、榜单和系统信息的查询与写操作。

## 功能可用性

| 操作 | 状态 |
|------|------|
| 读操作（列表、详情、用户、通知、榜单查询等） | 可用，优先使用 |
| 写操作（`article post` / `article update` / `comment post`） | 部分可用，不建议使用 |

**写操作存在已确认的服务端缺陷**：`commentContent` 会被服务端按纯文本处理，换行折叠为空格，Markdown 列表、分段与行内代码全部丢失；`articleContent` 的行为同样未经验证。已发布的内容无法通过 API 修正格式，只能人工到网页端手动改。

**因此：不要用 ldcli 执行发帖、回帖等写操作。** 用户需要发布或回帖时，将拟好的内容（含标题、标签）以 Markdown 文本形式交给用户，提示用户手动复制粘贴到论坛网页端完成发布。仅当用户明确坚持要求用 CLI 写入并知晓格式风险时，才可执行，且执行前须复述内容获得确认。

## 前置检查

1. 运行环境二选一：
   - 项目源码方式：`uv run ldcli <命令>`（在本项目根目录下）
   - 已打包的可执行文件：`dist\ldcli.exe <命令>`
2. 鉴权：Token 依次从 `--token` 参数、环境变量 `LDCLI_TOKEN`、配置文件 `~/.ldcli.toml` 读取。
3. 若命令返回 401（需要登录），提示用户到 ld246.com 的 设置-账号 页面复制 API Token，执行 `ldcli login <token>`（会先验证再保存），或临时用 `--token` 传入。**不要**猜测或编造 token。
4. 确认登录状态：`ldcli whoami`。

## 输出格式约定

| 模式 | 触发方式 | 用途 |
|------|----------|------|
| 简洁视图 | 默认 | 人类阅读，帖子列表为"序号+标题+摘要行"格式 |
| 完整视图 | `--full` | 对齐表格（ID/标题/作者/回帖/浏览），需要比对多条数据时使用 |
| 原始 JSON | `--json` | 需要提取未被简洁视图展示的字段（如链接、正文预览、分页信息）或做脚本处理时使用 |

解析数据时优先使用 `--json` 并从 JSON 中取值，不要解析人类可读输出。

## 常用工作流

### 浏览帖子

```bash
ldcli article list                     # 最新帖子（简洁视图），-s hot|good|reply|perfect 换排序
ldcli article list -p 2                # 翻页（页大小固定 20）
ldcli article domain Java -p 1         # 领域帖子列表
ldcli article tag Java -s hot          # 标签帖子列表
ldcli article show <id>                # 详情：正文 + 回帖；-p 翻回帖页
```

简洁视图中每条帖子行尾括号内是帖子 ID（如 `(1791335561953)`），后续 `article show`、回帖都要用它。

### 发布与回帖（写操作，部分可用，不建议使用，默认不要调用）

```bash
ldcli article post --title "标题" --tags "标签1,标签2" --content "正文"
ldcli article post --title ... --tags ... --file ./post.md   # 正文来自文件，- 表示 stdin
ldcli article update <id> --content "新正文"                 # 未指定的字段保持原值
ldcli comment post --article <帖子ID> --content "回帖内容"
ldcli comment post --article <id> --content "..." --reply <回帖ID>   # 楼中楼
```

- **不建议通过 CLI 发帖/回帖**：服务端会折叠换行、丢弃 Markdown 格式（见上文"功能可用性"）。需要发布内容时，把拟好的标题、标签、正文交给用户，由用户手动复制粘贴到论坛网页端。
- 仅在用户明确坚持用 CLI 写入时才执行，且须先向用户复述将要提交的标题、标签和内容，说明格式会被破坏，得到确认后再执行。
- 帖子 ID 与回帖 ID 从 `article show` 输出中获取；回帖 ID 在回帖行首的 `[...]` 中。

### 用户与通知

```bash
ldcli user show <用户名>          # 用户详情
ldcli user articles <用户名>      # 用户的帖子
ldcli user comments <用户名>      # 用户的回帖
ldcli notify unread               # 未读计数
ldcli notify list commented -p 1  # 消息列表，类型: commented|comment2ed|reply|at|following|point|broadcast|wallet|sys-announce
ldcli notify read commented       # 标记已读（仅 commented|comment2ed|reply|at|following）
```

### 其他

```bash
ldcli domain list / domain show <uri>   # 领域
ldcli tag list / tag show <uri>         # 标签
ldcli top newbies / top followers       # 榜单
ldcli system time                        # 服务器时间（也可用作连通性探测）
```

## 错误处理

| 现象 | 含义 | 处理 |
|------|------|------|
| `需要登录（401）` | Token 缺失或失效 | 引导用户 `ldcli login <token>`，勿自行重试 |
| `权限不足（403）` | 账号无该操作权限 | 如实告知用户，不重试 |
| `API 返回错误（code=…）` | 服务端业务错误 | 将 msg 原样转述给用户 |
| `网络请求失败` | 网络问题 | 检查网络后重试一次，仍失败则报告 |

客户端已内置限流（100 次/分钟），无需在命令间额外添加延时；也**不要**用循环高频调用列表接口抓取大量页面（社区禁止用于内容填充）。

## 参考

完整命令树与全部参数见 [references/commands.md](references/commands.md)。
