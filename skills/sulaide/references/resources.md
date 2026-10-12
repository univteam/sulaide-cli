# Sulaide resource library（查看与下载资源库）

Use only the shared `sulaide` CLI. Do not call undocumented HTTP routes, invent resource version IDs, or put an API key on a command line, in a file, or in a handoff.

## 1. Confirm sign-in and project first

`resources list` reads the authenticated Agent API, so run `sulaide auth status` first. If it fails with 401 or "Run `sulaide auth login`", follow `references/login.md` and come back. Take `PROJECT_ID` from `sulaide projects list` or `sulaide projects show PROJECT_ID`; never guess a project ID.

## 2. View the resource library

```bash
sulaide resources list PROJECT_ID                              # 资源库全部资源版本
sulaide resources list PROJECT_ID --resource-type export_pptx  # 按类型筛选
sulaide --pretty resources list PROJECT_ID                     # 缩进输出，便于和用户一起看
```

Resource types:

| `--resource-type` | 含义 |
| --- | --- |
| `upload` | 上传的源底稿 |
| `narrative_analysis` | 叙事分析稿 |
| `generated_image` | 生成图片 |
| `export_pptx` | 导出的 PPTX |
| `export_pdf` | 导出的 PDF |

Report exactly what the server returns: each resource's `resource_version_id`, type, filename, size, and any version or page fields present. Do not infer, renumber, or promise fields the response does not contain. Use `--page-number N` (从 1 开始) when the list is long and the user asks for older entries.

## 3. Download a resource

```bash
sulaide resources download RESOURCE_VERSION_ID --output PATH
```

- The CLI never overwrites: it fails with `Refusing to overwrite` when `PATH` already exists, so choose a fresh filename.
- The file is written atomically (`.part` then rename); an empty payload fails instead of leaving an empty file.
- Report the returned `path`, `size_bytes`, `filename`, and the resource version ID. Opening or inspecting the downloaded file is a separate validation step; do not claim it is correct or complete without checking it.

## 4. Handoff

Hand off the resource list itself, or the local file path together with the resource version ID and filename. Never print, log, or forward an API key or password, and never write resource data into a file the user did not ask for.

## Troubleshooting

Common failures are listed in the error table in `SKILL.md`: 401 means re-login, 503 `AGENT_API_DISABLED` means the server has the Agent API turned off, and 429 means the per-account read limit was hit — wait and retry the same call, do not poll in a loop. A 404 on a resource version means the ID does not exist (or is not visible to this account); re-list the project's resources instead of guessing another ID.
