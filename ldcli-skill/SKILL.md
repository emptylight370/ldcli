---
name: ldcli-skill
description: 使用 ldcli 命令行工具访问 ld246.com 论坛（黑客派/Symphony 社区）。此 skill 应在用户要求浏览帖子列表、查看帖子详情与回帖、发布回帖、查询领域/标签/用户信息、查看或处理通知、查看榜单，或提到 ldcli/论坛命令行时使用。注意：回帖须带 --content-type markdown（已验证）；发帖/改帖为部分可用状态，不建议使用，需要发布帖子时提示用户手动复制粘贴到论坛网页端。
---

# ldcli — ld246.com 论坛命令行

## 概述

`ldcli` 是 ld246.com 社区的命令行客户端，基于 ld246.com 的 API v2 实现。支持帖子（浏览/发布/更新）、回帖、领域、标签、用户、通知、榜单和系统信息的查询与写操作。

## 功能可用性

| 操作 | 状态 |
|------|------|
| 读操作（列表、详情、用户、通知、榜单查询等） | ✅ 可用，优先使用 |
| `comment post` / `comment update` 带 `--content-type markdown` | ✅ 可用（2026-11-02 实测验证） |
| `comment post` / `comment update` 不带 `--content-type` | ⚠️ 格式折叠，不要使用 |
| `article post` / `article update` | ⚠️ 部分可用，不建议使用（未验证） |

**写操作缺陷与缓解**：不声明内容类型时，服务端按纯文本处理提交内容，换行折叠为空格、Markdown 全部丢失（详见 `docs/comment-newline-diagnosis.md`）。`comment` 系列传 `--content-type markdown`（写入 `commentContentType`）已实测可正确渲染；不带该字段的用法不要使用。`comment update` 也可作为发布后修补格式的补救通道。`articleContent` 的类型声明未经验证，发帖/改帖仍建议手动复制粘贴到论坛网页端。

即使已验证可用，**任何发布/回帖操作前仍须先向用户复述将要提交的内容，得到明确确认后再执行**；回帖无删除 API，发布后无法撤回。

## 前置检查

1. 运行环境任选其一：
   - 项目源码方式：`uv run ldcli <命令>`（在本项目根目录下）
   - 已打包的可执行文件：`build\ldcli.exe <命令>`
   - 用户自行安装的可执行文件：`ldcli <命令>`（在环境变量中可调用）
2. 鉴权：Token 依次从 `--token` 参数、环境变量 `LDCLI_TOKEN`（或回退 `LD_TOKEN`）、配置文件 `~/.ldcli.toml` 读取。
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

### 发布与回帖（写操作，须先获得用户明确确认）

```bash
ldcli article post --title "标题" --tags "标签1,标签2" --content "正文"   # ⚠️ 未验证，建议手动发布
ldcli article update <id> --content "新正文"                             # ⚠️ 未验证，建议手动修改
ldcli comment post --article <帖子ID> --content "回帖内容" --content-type markdown
ldcli comment post --article <id> --content "..." --reply <回帖ID> --content-type markdown   # 楼中楼
ldcli comment update <回帖ID> --content "新内容" --content-type markdown # 更新自己的回帖（修补格式用）
```

- **回帖必须带 `--content-type markdown`**（已实测验证），否则换行与 Markdown 会被服务端折叠。
- **发帖/改帖不要用 CLI**：`articleContent` 的类型声明未经验证，需要发布时把拟好的标题、标签、正文交给用户，由用户手动复制粘贴到论坛网页端。
- 任何发布/更新/回帖操作前，先向用户复述将要提交的标题、标签和内容，得到确认后再执行；回帖无删除 API，发布后无法撤回。
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
ldcli system time                       # 服务器时间（也可用作连通性探测）
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
