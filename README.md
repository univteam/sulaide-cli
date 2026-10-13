<p align="center">
  <a href="https://www.sulide.com.cn">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/logo-wordmark-color-on-dark.png">
      <img src="assets/logo-wordmark-color.png" alt="速来得" width="360">
    </picture>
  </a>
</p>

<p align="center">
  <a href="https://github.com/univteam/sulaide-cli/actions/workflows/ci.yml"><img src="https://github.com/univteam/sulaide-cli/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/univteam/sulaide-cli" alt="License: Apache-2.0"></a>
</p>

<p align="center">
  <a href="https://www.sulide.com.cn">官网</a> ·
  <a href="https://www.sulide.com.cn/register">注册</a> ·
  <a href="https://www.sulide.com.cn/login">登录</a> ·
  <a href="#english">English</a>
</p>

# 速来得 · AI PPT 助手

**把已有材料，变成一份专业、可编辑的汇报。**

速来得面向需要把研究底稿、汇报材料、企业文档快速转成专业演示文稿的人：企业汇报、咨询分析、市场研究、投融资材料、教学培训等场景中，有底稿和业务判断、但缺少时间或设计资源完成版式与 PPTX 封装的内容生产者。

上传底稿，梳理叙事，生成页面，导出可编辑 PPTX —— 交付的是 PPTX，不是一次性图片。

### 工作流

1. **底稿上传**：导入 Word、PDF、PPTX、表格或直接粘贴文本。
2. **叙事分析**：先确认故事线、页面职责和主要结论。
3. **报告预览**：逐页检查版式、文字和内容图，随时重新生成。
4. **PPTX 导出**：带着母版、Logo、页脚和可编辑文字一起交付。

### 特点

- **尽量保留原本的语言**：复用底稿中的观点、措辞和表达习惯，不把专业判断改成千篇一律的 AI 文案。
- **母版和内容分层处理**：标题、品牌标识、页脚和页码由母版管理，AI 专注在内容区完成视觉表达。
- **交付后仍然可继续编辑**：导出可编辑 PPTX，汇报前改项目名、换标题或调整单页，不需要重做整份文档。
- **设计品牌母版**：针对格式要求较高的汇报，可先设置 Logo、字体、页脚和版式规范。

👉 立即体验：[www.sulide.com.cn](https://www.sulide.com.cn)

---

## sulaide-cli：让编码 Agent 使用速来得

本仓库是速来得 Agent API 的命令行客户端 `sulaide`，以及配套的 `sulaide` skill。装好后，Claude Code、Codex、Cursor、Gemini CLI、GitHub Copilot 等编码 Agent 可以直接帮你把材料做成 PPT：登录 → 上传底稿 → 叙事分析 → 预览 → 导出 PPTX。

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
sulaide auth invite-code # 查看本账户邀请码（注册时自动缓存，可转发给他人）
sulaide auth logout     # 删除本地保存的 Key
sulaide credits         # 查询剩余积分（JSON）；--human 输出一行中文摘要
sulaide coupons --status available --human   # 查询卡券（只读，可按状态筛选）
```

登录后 Key 保存在 `~/.sulaide/auth.json`（目录 `0700`，文件 `0600`），工作流命令会自动使用。密码只会交互输入，不接受命令行参数。

### 资源库（查看与下载项目资源）

```bash
sulaide projects list                                   # 查看已有项目
sulaide resources list PROJECT_ID                       # 查看项目资源库中的资源版本
sulaide resources list PROJECT_ID --resource-type export_pptx   # 按类型筛选（upload / narrative_analysis / generated_image / export_pptx / export_pdf）
sulaide resources download RESOURCE_VERSION_ID --output FILE   # 下载资源库中的一个资源版本
```

`resources download` 不会覆盖已存在的文件（先写 `.part` 再原子改名），输出为 JSON（`path`、`size_bytes`、`filename` 等）。

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
| 项目 | `references/projects.md` | `sulaide projects list` 获取项目列表，`projects show` 查看详情，复用或新建项目 |
| 资源库 | `references/resources.md` | `sulaide resources list` 查看项目资源库，`resources download` 下载资源文件 |
| 1. 素材 | `references/source.md` | 准备或更新项目素材（文本） |
| 2. 分析 | `references/analysis.md` | 运行或恢复叙事分析，返回大纲和执行状态 |
| 3. 预览 | `references/preview.md` | 生成并检查演示预览，含逐页成功/失败状态 |
| 4. 导出 | `references/export.md` | 基于冻结的演示版本校验并下载 PPTX |

`SKILL.md` 还包含前置条件、路由规则和常见错误（401、503 `AGENT_API_DISABLED`、限流、冲突、积分不足等）。`references/*.md` 没有 frontmatter，Agent 不会把它们列为独立 skill。

### 一步安装到编码 Agent

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

- CLI 调用速来得 的 Agent API v1（`/api/agent/v1/*`），使用个人 Agent API Key 认证，费用从账户积分扣除，Key 不会单独产生余额，也不继承管理员权限。
- Key 可在网页「账户 → API Keys」创建或吊销；新建的密钥只显示一次。`sulaide auth register` / `sulaide auth login` 会自动创建并保存 Key。
- 服务端可能关闭 Agent API，此时命令会返回错误；用 `sulaide auth status` 查看当前启用的能力。
- 按账户限流：默认每分钟 120 次读、10 次写。
- `sulaide credits` 调用只读的 `GET /api/agent/v1/credits`，返回 Key 所属账户的 `available` 与 `balance`；若服务端尚未提供该接口会返回 404。
- `sulaide coupons` 调用只读的 `GET /api/agent/v1/coupons`，列出账户的卡券（名称、金额、状态、有效期），可用 `--status available|not_started|used|expired|voided` 筛选；不返回兑换码，也不能通过 CLI 兑换或使用卡券。
- 目前素材只支持 UTF-8 文本；PDF、Office、表格、图片等需通过网页上传。
- 资源库命令（`sulaide resources list` / `resources download`）读取并下载项目的资源版本：源底稿、叙事分析稿、生成图片、导出 PPTX/PDF。
- 每个 operation 的 request ID 是其恢复标识：响应丢失后请查询原 operation，不要新建请求。

## 许可证

[Apache License 2.0](LICENSE)

---

<a id="english"></a>

## English

**Sulaide (速来得) is an AI PPT assistant that turns your existing material into a professional, editable presentation.** Upload a draft (Word, PDF, PPTX, spreadsheets, or pasted text), confirm the narrative and page roles, review and regenerate pages, then export an editable PPTX with your master slides, logo, footer, and editable text — not a one-off image.

This repository provides the `sulaide` CLI for the Sulaide Agent API and a `sulaide` agent skill, so coding agents such as Claude Code, Codex, Cursor, Gemini CLI, and GitHub Copilot can run the workflow for you. Install with `uv tool install git+https://github.com/univteam/sulaide-cli.git`; see the install table above for one-step plugin setup.

Website: [www.sulide.com.cn](https://www.sulide.com.cn) · [Sign up](https://www.sulide.com.cn/register) · [Log in](https://www.sulide.com.cn/login) · License: [Apache-2.0](LICENSE)

