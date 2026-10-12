# sulaide-cli

速来PPT（Sulaide）Agent API 的命令行客户端，以及配套的「四步法」工作流 skill。

## 安装

需要先安装 [uv](https://docs.astral.sh/uv/)。

```bash
uv tool install git+https://github.com/univteam/sulaide-cli.git
# 升级
uv tool upgrade sulaide-cli
# 不安装、临时运行一次
uvx --from git+https://github.com/univteam/sulaide-cli.git sulaide auth status
# 本地 checkout 中安装
uv tool install .
```

## 使用

```bash
sulaide auth register   # 注册账号并初始化 CLI 访问
sulaide auth login      # 登录已有账号，创建个人 Agent API Key
sulaide auth status     # 查看当前启用的能力
sulaide auth logout     # 删除本地保存的 Key
```

登录后 Key 保存在 `~/.sulaide/auth.json`（目录 `0700`，文件 `0600`），工作流命令会自动使用。密码只会交互输入，不接受命令行参数。

### 环境变量

| 变量 | 说明 |
| --- | --- |
| `SULAIDE_BASE_URL` | API 地址，**默认生产环境 `https://www.sulide.com.cn`**。可通过该变量指向其他部署（如 `https://api.example.com`）。远程地址必须是 HTTPS（localhost 可用 HTTP）。 |
| `SULAIDE_API_KEY` | 直接注入的 Agent API Key，优先于本地保存的 Key。托管 Agent 运行时请通过其密钥存储注入。 |
| `SULAIDE_STATE_DIR` | 本地状态目录，默认 `~/.sulaide`。 |

不要把 Key 写进 prompt、shell 历史、skill 文件或交接文档。

## `sulaide` skill

只有一个 skill：`skills/sulaide/`。用户只需启用 `sulaide`，它会按需读取 `references/` 下的分步指南：

| 步骤 | 文件 | 内容 |
| --- | --- | --- |
| 登录 | `references/login.md` | 安装检查、注册/登录、安全保存 API Key、`sulaide auth status` 验证 |
| 1. 素材 | `references/source.md` | 准备或更新项目素材（文本） |
| 2. 分析 | `references/analysis.md` | 运行或恢复叙事分析，返回大纲和执行状态 |
| 3. 预览 | `references/preview.md` | 生成并检查演示预览，含逐页成功/失败状态 |
| 4. 导出 | `references/export.md` | 基于冻结的演示版本校验并下载 PPTX |

`SKILL.md` 还包含前置条件、路由规则和常见错误（401、503 `AGENT_API_DISABLED`、限流、冲突、积分不足等）。`references/*.md` 没有 frontmatter，Agent 不会把它们列为独立 skill。

### 一步安装到编码 Agent

> **仓库目前是私有的。** 所有插件/扩展安装都会通过 git 拉取本仓库，需要本机对 `univteam/sulaide-cli` 有访问权限：先 `gh auth login`，再 `gh auth setup-git`（或配置好 SSH key）。

| Agent | 安装（一次） | 更新 |
| --- | --- | --- |
| Claude Code | `/plugin marketplace add univteam/sulaide-cli` 然后 `/plugin install sulaide@sulaide` | `/plugin marketplace update sulaide` |
| Codex | `codex plugin marketplace add univteam/sulaide-cli && codex plugin add sulaide@sulaide` | `codex plugin marketplace upgrade sulaide` |
| GitHub Copilot CLI | `copilot plugin marketplace add univteam/sulaide-cli && copilot plugin install sulaide@sulaide` | `copilot plugin update sulaide@sulaide` |
| Gemini CLI | `gemini extensions install https://github.com/univteam/sulaide-cli` | `gemini extensions update sulaide` |
| Cursor | 团队管理员在 Dashboard → Plugins 导入本仓库（`.cursor-plugin/`）；或用下方 CLI 命令 | 同左 / `sulaide skills update` |
| OpenCode、Windsurf、Amp、Pi、Hermes 及其他读取 `~/.agents/skills` 的 Agent | `sulaide skills install` | `sulaide skills update` |

### `sulaide skills` 命令

没有插件系统的 Agent，直接用 CLI 把随包附带的 skill 复制到它们的 skill 目录（`uv tool install` 会带上 skill 文件）：

```bash
sulaide skills list                     # 查看检测到的 Agent 和安装状态
sulaide skills install                  # 安装到自动检测到的所有 Agent
sulaide skills install --agent opencode # 只装某一个，可重复 --agent
sulaide skills install --all            # 装到所有已知 Agent 目录
uv tool upgrade sulaide-cli && sulaide skills update   # 升级 CLI 并刷新已安装的 skill
sulaide skills uninstall --agent opencode
```

支持的 `--agent`：`claude`、`codex`、`cursor`、`gemini`、`copilot`、`opencode`、`windsurf`、`amp`、`pi`、`hermes`、`agents`（通用 `~/.agents/skills`）。不会覆盖不是由 sulaide 安装的同名目录，除非加 `--force`。旧版本单独安装的 `sulaide-source` 等目录，只要带有 sulaide 安装标记，会在 install/update/uninstall 时自动清理；没有标记的同名目录不会被动。

### 单独打包

```bash
uv run scripts/package-workflow-skills.py   # 输出 dist/workflow-skills/sulaide-<版本>.zip
```

### 维护说明

`skills/` 是唯一的 skill 源。各 Agent 的插件清单（`plugin.json`、`.claude-plugin/`、`.codex-plugin/`、`.agents/plugins/`、`.cursor-plugin/`、`gemini-extension.json`）都由 `pyproject.toml` 的版本号生成，改版本后运行：

```bash
uv run scripts/sync-plugin-manifests.py
```

CI 会用 `--check` 校验清单没有过期，并用官方 schema 校验 Agent Plugins / Cursor 清单、用 `claude plugin validate` 校验 Claude Code 清单。

## 开发

```bash
uv sync
uv run pytest
```

## Agent API 说明

- CLI 调用速来PPT 的 Agent API v1（`/api/agent/v1/*`），使用个人 Agent API Key 认证，费用从账户积分扣除，Key 不会单独产生余额，也不继承管理员权限。
- Key 可在网页「账户 → API Keys」创建或吊销；新建的密钥只显示一次。`sulaide auth register` / `sulaide auth login` 会自动创建并保存 Key。
- 服务端可能关闭 Agent API，此时命令会返回错误；用 `sulaide auth status` 查看当前启用的能力。
- 按账户限流：默认每分钟 120 次读、10 次写。
- 目前素材只支持 UTF-8 文本；PDF、Office、表格、图片等需通过网页上传。
- 每个 operation 的 request ID 是其恢复标识：响应丢失后请查询原 operation，不要新建请求。

## 许可证

[Apache License 2.0](LICENSE)
