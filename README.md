# cli

本 CLI 用于访问链滴社区并读取可读内容，提供经过封装的访问论坛的方法，免于拼接 HTTP 请求。

## 使用方法

1. 编译或安装项目
2. 安装[附带 skill](ldcli-skill/) 至 Agent skill 目录
3. 登录 CLI
4. 通过 `ldcli` 命令使用 CLI

### 登录方法

1. 通过 `ldcli login <token>` 登录，其中 `<token>` 从账号设置页面自行复制
2. 通过环境变量 `LDCLI_TOKEN` 设置 token
3. 通过 `--token` 参数临时传入

### 可用能力

1. 读取：如获取帖子列表、读取帖子内容等
2. 写入功能未完善，如发布帖子、回复帖子等

详情查看 `--help` 文档。
