# ldcli 完整命令参考

## 功能可用性

| 命令 | 状态 |
|------|------|
| 所有读命令（list / show / 用户 / 通知 / 榜单 / system time） | ✅ 可用 |
| `article post` / `article update` / `comment post` | ⚠️ 部分可用，不建议使用 |

写操作缺陷：服务端按纯文本处理提交内容，换行折叠为空格、Markdown 列表/分段/行内代码丢失，且无法通过 API 修正，只能人工到网页端改格式（详见 `docs/comment-newline-diagnosis.md`）。需要发布内容时，提示用户手动复制粘贴到论坛网页端。

全局参数（可置于任意位置）：

| 参数 | 说明 |
|------|------|
| `--json` | 输出服务端原始 JSON，替代人类可读格式 |
| `--token <token>` | 临时指定 API Token（优先级：`--token` > 环境变量 `LDCLI_TOKEN` > 配置文件 `~/.ldcli.toml`） |
| `--version` | 查看版本 |
| `--help` | 各级子命令均支持 |

分页通用约定：列表类命令用 `-p/--page` 指定页号（默认 1，页大小固定 20）；排序用 `-s/--sort`，可选 `time`（默认）/`hot`（热议）/`good`（好评）/`reply`（最近回帖）/`perfect`（优选）。

## login / logout / whoami

```bash
ldcli login [token]   # 录入 API Token；省略参数则交互输入；保存前会调用 /api/v2/user 验证
ldcli logout          # 清除本地保存的 Token
ldcli whoami          # 当前登录用户详情
```

## article（帖子）

```bash
ldcli article list [-s sort] [-p page] [--full]
    # 最新帖子列表；默认简洁视图，--full 输出表格

ldcli article domain <uri> [-p page] [--full]
    # 领域帖子列表，如 ldcli article domain Java

ldcli article tag <uri> [-s sort] [-p page] [--full]
    # 标签帖子列表

ldcli article show <id> [-p page]
    # 帖子详情：元信息 + 正文 + 回帖；-p 为回帖页号
    # 回帖多页时输出翻页提示；--json 时返回完整结构（article + pagination）

ldcli article post --title <标题> --tags <标签,逗号分隔>   # ⚠️ 部分可用，不建议使用
                   (--content <正文> | --file <路径|"-" 表示 stdin>)
                   [--reward-content <打赏区内容>] [--reward-point <积分>]

ldcli article update <id> [--title ...] [--tags ...]       # ⚠️ 部分可用，不建议使用
                     [--content ... | --file ...]
                     [--reward-content ...] [--reward-point ...]
    # 仅更新指定字段，其余保持原值；articleType 由客户端自动取原值回传
    # ⚠️ 服务端按纯文本处理正文：换行折叠为空格，Markdown 格式丢失；已发布内容只能到网页端手动修格式
```

## comment（回帖）

```bash
ldcli comment post --article <帖子ID> (--content <内容> | --file <路径>)   # ⚠️ 部分可用，不建议使用
                   [--reply <被回复的回帖ID>]
    # --reply 用于楼中楼回复；回帖 ID 见 article show 输出中每条回帖行首 [...]
    # ⚠️ 服务端按纯文本处理回帖：换行折叠为空格，Markdown 列表/行内代码不渲染；建议手动复制粘贴到网页端回帖
```

## domain（领域）

```bash
ldcli domain list [-p page]     # 领域列表
ldcli domain show <uri>         # 领域详情，如 ldcli domain show Java
```

## tag（标签）

```bash
ldcli tag list [-p page]        # 标签列表
ldcli tag show <uri>            # 标签详情
```

## user（用户）

```bash
ldcli user show <name>                      # 按用户名查详情
ldcli user no <userNo>                      # 按用户序号查详情
ldcli user articles <name> [-p page]        # 用户帖子列表
ldcli user comments <name> [-p page]        # 用户回帖列表
ldcli user events <name> [--size 1-64]      # 近期动态，默认 16 条
ldcli user watching <name> [-p page]        # 关注的帖子
ldcli user following <name> --type users|tags|articles [-p page]
ldcli user followers <name> [-p page]       # 关注者列表
```

## notify（通知）

```bash
ldcli notify unread              # 未读消息计数
ldcli notify list <type> [-p page]
    # type: commented | comment2ed | reply | at | following
    #       | point | broadcast | wallet | sys-announce
ldcli notify read <type>
    # 仅支持: commented | comment2ed | reply | at | following
    # broadcast/wallet/sys-announce 拉取后自动已读，无需调用
```

## top（榜单）

```bash
ldcli top newbies      # 新注册用户
ldcli top followers    # 粉丝榜
```

## system

```bash
ldcli system time      # 服务器当前时间，亦可用作登录态/连通性探测
```

## 简洁视图字段说明（article list）

保留：序号、标题（优选帖加 `[精]` 前缀）、作者、标签、回帖数（0 时省略）、相对时间、帖子 ID（行尾括号）。
隐藏：正文预览、头像/缩略图 URL、完整作者与标签对象、精确时间戳、浏览数、链接、置顶/投票/感谢等元数据。
需要被隐藏的字段时，使用 `--json` 从原始数据中提取。

## 已知实现要点（与 API 文档的实测差异）

- 帖子详情接口响应结构为 `{pagination, article}`，回帖在 `article.articleComments` 中
- `articleContent` / `commentContent` 为 HTML 片段，人类可读输出已转换为纯文本并保留段落
- 服务端对所有 API 校验登录态，未带有效 Token 一律返回 401
- 客户端内置限流约 100 次/分钟（服务端上限 120 次/分钟/IP）
