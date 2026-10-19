from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import secrets
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import httpx


DEFAULT_BASE_URL = "https://www.sulide.com.cn"


def _base_url() -> str:
    value = (os.environ.get("SULAIDE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    parsed = urlparse(value)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
        raise ValueError("SULAIDE_BASE_URL must use HTTPS (HTTP is allowed for localhost)")
    return value


def _state_file() -> Path:
    root = _state_dir()
    return root / "operations.json"


def _state_dir() -> Path:
    root = Path(os.environ.get("SULAIDE_STATE_DIR", Path.home() / ".sulaide")).expanduser()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root


def _auth_file() -> Path:
    return _state_dir() / "auth.json"


def _read_auth() -> dict:
    try:
        value = json.loads(_auth_file().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_auth(value: dict) -> None:
    path = _auth_file()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)


def _read_state() -> dict:
    try:
        value = json.loads(_state_file().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(state: dict) -> None:
    path = _state_file()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)


class Client:
    def __init__(self):
        self.key = os.environ.get("SULAIDE_API_KEY", "") or str(_read_auth().get("api_key", ""))
        if not self.key:
            raise ValueError("Run `sulaide auth login` or set SULAIDE_API_KEY")
        self.base = _base_url() + "/api/agent/v1"
        self.http = httpx.Client(timeout=httpx.Timeout(30, read=90), follow_redirects=False,
                                 headers={"Authorization": f"Bearer {self.key}", "Accept": "application/json"})

    def request(self, method: str, path: str, *, params=None, json_body=None, stream=False):
        if params:
            params = {key: value for key, value in params.items() if value is not None}
        response = self.http.request(method, self.base + path, params=params or None, json=json_body)
        if response.is_error:
            raise _http_error(response)
        if stream:
            return response
        return _unwrap(response.json())


def _error_detail(body: dict) -> dict:
    """Sulaide envelope ``{code, message, data, traceId}`` or FastAPI ``{detail}``."""
    if isinstance(body.get("detail"), dict):
        return body["detail"]
    if "detail" in body:
        return {"message": str(body["detail"])}
    detail = {"code": body.get("code"), "message": body.get("message") or "请求失败"}
    if isinstance(body.get("data"), dict):
        detail.update({k: v for k, v in body["data"].items() if k in ("reason", "retryable")})
    if body.get("traceId"):
        detail["trace_id"] = body["traceId"]
    return detail


def _http_error(response) -> "ApiError":
    try:
        body = response.json()
    except ValueError:
        return ApiError(response.status_code, response.text)
    if not isinstance(body, dict):
        return ApiError(response.status_code, response.text)
    return ApiError(response.status_code, _error_detail(body))


def _unwrap(body):
    """Business errors arrive as HTTP 200 with ``code != 0``; never return ``data: null`` as success."""
    if isinstance(body, dict) and "code" in body and body.get("code") not in (0, None):
        try:
            status = int(body["code"])
        except (TypeError, ValueError):
            status = 400
        raise ApiError(status, _error_detail(body))
    return body.get("data", body) if isinstance(body, dict) else body


def _check_download_response(response) -> None:
    """Raise before anything touches disk unless the body is a real PPTX (ZIP) file.

    Business errors arrive as HTTP 200 + JSON ``{code, message}``; never write them as a file."""
    if response.is_error:
        raise _http_error(response)
    content = response.content or b""
    if "application/json" in response.headers.get("content-type", "") or content[:1] == b"{":
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            _unwrap(body)  # raises ApiError for code != 0
        raise ValueError("下载结果不是 PPTX 文件（服务端返回了 JSON）")
    if not content.startswith(b"PK"):
        raise ValueError("Downloaded artifact is not a PPTX ZIP package")


def _auth_request(method: str, path: str, *, token: str | None = None, json_body=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=30, follow_redirects=False, headers=headers) as client:
        response = client.request(method, _base_url() + path, json=json_body)
    if response.is_error:
        raise _http_error(response)
    return _unwrap(response.json())


def _auth_login(username: str, password: str) -> dict:
    return _auth_request("POST", "/api/auth/login", json_body={"username": username, "password": password})


def _registration_credentials(args) -> tuple[str, str, str, str | None]:
    username = args.username or input("用户名: ").strip()
    email = args.email or input("邮箱: ").strip()
    password = getpass.getpass("密码（输入时不显示）: ")
    confirmation = getpass.getpass("再次输入密码: ")
    if password != confirmation:
        raise ValueError("两次输入的密码不一致")
    if len(password) < 6:
        raise ValueError("密码至少需要 6 个字符")
    invite_code = args.invite_code or input("邀请码（可选，直接回车跳过）: ").strip() or None
    return username, email, password, invite_code


def _captcha_answer(email: str) -> str:
    challenge = _auth_request("GET", "/api/captcha/generate")
    image = base64.b64decode(challenge["image_base64"], validate=True)
    image_path = _state_dir() / "registration-captcha.png"
    image_path.write_bytes(image)
    try:
        image_path.chmod(0o600)
    except OSError:
        pass
    opened = webbrowser.open(image_path.resolve().as_uri()) if sys.stdin.isatty() else False
    print(f"请查看验证码图片：{image_path}" + ("（已尝试在浏览器打开）" if opened else ""), file=sys.stderr)
    answer = getpass.getpass("请输入图片中的计算结果: ").strip()
    _auth_request("POST", "/api/auth/verification-code/send", json_body={
        "email": email, "captcha_token": challenge["token"], "captcha_answer": answer,
    })
    image_path.unlink(missing_ok=True)
    return input("请输入邮件中的 6 位验证码: ").strip()


INVITE_CODE_ENDPOINT = "/api/credits/invite-code"


def _fetch_invite_code(token: str) -> str | None:
    """Best-effort: return the account's invite code, or None if unavailable."""
    try:
        payload = _auth_request("GET", INVITE_CODE_ENDPOINT, token=token)
    except ApiError:
        return None
    if isinstance(payload, dict):
        code = payload.get("invite_code") or payload.get("code")
        return str(code) if code else None
    return None


def _save_api_key(token: str, username: str, role: str) -> dict:
    account = _auth_request("GET", "/api/account/me", token=token)
    created = _auth_request("POST", "/api/account/api-keys", token=token,
                            json_body={"name": "Sulaide CLI"})
    previous = _read_auth()
    previous_key_revoked = not previous.get("api_key")
    if previous.get("account_id") == account["id"] and previous.get("api_key_id"):
        try:
            _auth_request("DELETE", f"/api/account/api-keys/{previous['api_key_id']}", token=token)
            previous_key_revoked = True
        except ApiError:
            pass
    auth = {
        "account_id": account["id"], "username": username, "role": role,
        "api_key_id": created["id"], "api_key": created["secret"],
    }
    invite_code = _fetch_invite_code(token)
    if invite_code:
        auth["invite_code"] = invite_code
    _write_auth(auth)
    message = "API Key 已保存到本机权限受限的文件，可直接调用 Agent API。"
    if invite_code:
        message += f"邀请码：{invite_code}（可用 `sulaide auth invite-code` 查看）。"
    if not previous_key_revoked:
        message += "旧账户的本地 Key 未能由这次登录撤销；如果不再使用，请到原账户的 API Key 页面撤销。"
    return {"username": username, "role": role, "api_key_saved": True,
            "api_key_id": created["id"], "message": message}


def _auth_command(args) -> dict:
    if args.action == "status":
        client = Client()
        result = client.request("GET", "/capabilities")
        result["authenticated_as"] = "environment API key" if os.environ.get("SULAIDE_API_KEY") else (_read_auth().get("username") or "local API key")
        return result
    if args.action == "login":
        username = args.username or input("用户名或邮箱: ").strip()
        password = getpass.getpass("密码（输入时不显示）: ")
        result = _auth_login(username, password)
        return _save_api_key(result["token"], result["username"], result["role"])
    if args.action == "register":
        username, email, password, invite_code = _registration_credentials(args)
        legal = _auth_request("GET", "/api/auth/legal-config")
        print(f"隐私政策版本：{legal['privacy_policy_version']}；服务条款版本：{legal['terms_version']}", file=sys.stderr)
        print(f"请先在官网注册页阅读《隐私政策》和《服务条款》：{_base_url()}/register", file=sys.stderr)
        consent = input("输入 yes 表示同意上述条款并注册: ").strip().lower()
        if consent != "yes":
            raise ValueError("未同意条款，已取消注册")
        verification_enabled = _auth_request("GET", "/api/auth/email-verification-config").get("enabled", False)
        verification_code = _captcha_answer(email) if verification_enabled else None
        registered = _auth_request("POST", "/api/auth/register", json_body={
            "username": username, "email": email, "password": password,
            "invite_code": invite_code, "verification_code": verification_code,
            "accepted_legal": True, "privacy_policy_version": legal["privacy_policy_version"],
            "terms_version": legal["terms_version"],
        })
        return _save_api_key(registered["token"], registered["username"], registered["role"])
    if args.action == "logout":
        path = _auth_file()
        path.unlink(missing_ok=True)
        message = "已删除本地保存的 API Key；如需立即失效，请在账户的 API Key 页面撤销它。"
        if os.environ.get("SULAIDE_API_KEY"):
            message += "当前 SULAIDE_API_KEY 环境变量仍然有效，需从运行环境中移除。"
        return {"logged_out": True, "message": message}
    if args.action == "invite-code":
        stored = _read_auth()
        invite_code = stored.get("invite_code")
        if not invite_code:
            raise ValueError("本地未保存邀请码；运行 `sulaide auth login`（或 `sulaide auth register`）后即可获取")
        return {
            "invite_code": invite_code,
            "register_url": f"{_base_url()}/register?invite_code={invite_code}",
            "message": "把邀请码或注册链接发给被邀请人，注册时填写即可（邀请码为可选项）。",
        }
    raise ValueError("Unsupported auth command")


class ApiError(Exception):
    def __init__(self, status: int, detail):
        self.status = status
        self.detail = detail
        super().__init__(str(detail))


def _request_id(command: str, explicit: str | None) -> str:
    key = f"{command}:{explicit or 'latest'}"
    state = _read_state()
    if explicit:
        state[key] = explicit
        _write_state(state)
        return explicit
    existing = state.get(key)
    if existing:
        return str(existing)
    request_id = secrets.token_urlsafe(18)
    state[key] = request_id
    _write_state(state)
    return request_id


def _remember_operation(command: str, request_id: str, operation_id: str | None) -> None:
    if not operation_id:
        return
    state = _read_state()
    state[f"operation:{command}:{request_id}"] = operation_id
    # Retain the request ID only until we have a durable response. A later
    # intentional invocation gets a fresh ID; a lost response reuses this one.
    state.pop(f"{command}:latest", None)
    _write_state(state)


def _emit(value, *, json_mode: bool = True) -> None:
    if json_mode:
        print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2))


def _credits_summary(result: dict) -> str:
    return f"可用积分：{result.get('available')}（账户余额：{result.get('balance')}）"


COUPON_STATUS_LABELS = {"available": "可用", "not_started": "未生效", "used": "已使用",
                        "expired": "已过期", "voided": "已作废"}


def _coupons_summary(result: dict) -> str:
    items = result.get("items") or []
    if not items:
        return "没有符合条件的卡券"
    lines = [f"共 {result.get('total', len(items))} 张卡券："]
    for item in items:
        until = (item.get("valid_until") or "")[:10]
        label = COUPON_STATUS_LABELS.get(item.get("status"), item.get("status"))
        lines.append(f"- {item.get('name')}：¥{item.get('amount')}，{label}，有效期至 {until}")
    return "\n".join(lines)


def _wait(client: Client, operation_id: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    delay = 1.0
    while time.monotonic() < deadline:
        result = client.request("GET", f"/operations/{operation_id}")
        run = result.get("run")
        if not run or run.get("status") in {"completed", "failed", "cancelled"}:
            return result
        print(f"{run.get('status')} {run.get('progress', 0)}% {run.get('current_step') or ''}".strip(), file=sys.stderr)
        time.sleep(delay)
        delay = min(delay * 1.6, 10)
    raise TimeoutError(f"Wait timed out for operation {operation_id}; it was not cancelled")


NARRATIVE_PREFERENCES = {"rigorous": "rigorous_structure", "fluent": "fluent_expression"}


def _source_options(args) -> dict:
    """Project-settings fields for a source save. Only values the user set are sent.

    ``narrative_preference`` is included only when ``--narrative`` is set, so a
    content-only save does not force ``rigorous_structure``. Omitting it is meant
    to leave the saved preference unchanged. If the server still fills a missing
    field with ``rigorous_structure``, that reset remains a server-side default.
    """
    if args.target_pages is not None and not 1 <= args.target_pages <= 50:
        raise ValueError("--target-pages 必须在 1–50 之间")
    narrative = NARRATIVE_PREFERENCES[args.narrative] if args.narrative else None
    options = {
        "project_title": args.title, "language": args.language, "target_page_count": args.target_pages,
        "style_id": args.style_id, "source_page_count": args.source_page_count,
        "narrative_preference": narrative,
    }
    return {key: value for key, value in options.items() if value is not None}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sulaide", description="Use the Sulaide Agent workflow API")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--version", action="store_true", help="显示版本（含 git 提交）")
    sub = parser.add_subparsers(dest="area", required=True)

    auth = sub.add_parser("auth").add_subparsers(dest="action", required=True)
    auth.add_parser("status")
    register = auth.add_parser("register", help="交互式创建账户并保存 Agent API Key")
    register.add_argument("--username")
    register.add_argument("--email")
    register.add_argument("--invite-code")
    login = auth.add_parser("login", help="登录并保存 Agent API Key")
    login.add_argument("--username", help="用户名或邮箱；密码始终交互式输入")
    auth.add_parser("invite-code", help="查看本账户的邀请码（可转发给被邀请人）")
    auth.add_parser("logout", help="删除本机保存的 API Key")
    projects = sub.add_parser("projects").add_subparsers(dest="action", required=True)
    projects.add_parser("list")
    show = projects.add_parser("show"); show.add_argument("project_id", type=int)
    create = projects.add_parser("create"); create.add_argument("--title", default="新PPT"); create.add_argument("--request-id")
    create.add_argument("--language", choices=("zh", "en"), help="输出语言，默认 zh")

    source = sub.add_parser("source").add_subparsers(dest="action", required=True)
    upload = source.add_parser("upload"); upload.add_argument("project_id", type=int); upload.add_argument("file", type=Path); upload.add_argument("--request-id"); upload.add_argument("--expected-revision", type=int)
    set_source = source.add_parser("set"); set_source.add_argument("project_id", type=int); set_source.add_argument("--text"); set_source.add_argument("--file", type=Path); set_source.add_argument("--request-id"); set_source.add_argument("--expected-revision", type=int)
    for sp in (upload, set_source):
        sp.add_argument("--title", help="项目标题")
        sp.add_argument("--language", choices=("zh", "en"), help="输出语言（默认沿用项目语言，zh）")
        sp.add_argument("--target-pages", type=int, help="页数设定：严格按此页数规划叙事结构（1–50）")
        sp.add_argument("--narrative", choices=("rigorous", "fluent"), default=None,
                        help="叙事偏好：rigorous=严谨架构，fluent=流利表达；不传则不发送该字段")
        sp.add_argument("--style-id", type=int, help="母版 ID（见 `sulaide styles list`）；不传则用项目默认固定层")
        sp.add_argument("--source-page-count", type=int, help="底稿本身的页数（仅记录，可省略）")

    analysis = sub.add_parser("analysis").add_subparsers(dest="action", required=True)
    start = analysis.add_parser("start"); start.add_argument("project_id", type=int); start.add_argument("--request-id"); start.add_argument("--page-count", type=int, help="本次分析页数（1–50），覆盖已保存的页数设定；省略则用项目设定"); start.add_argument("--expected-revision", type=int)
    start.add_argument("--structure-requirements", help="结构要求（可选），例如：按问题、证据、建议组织")
    styles = sub.add_parser("styles", help="母版（PPT 模板）").add_subparsers(dest="action", required=True)
    styles.add_parser("list", help="列出可用母版及其 ID")
    preview = sub.add_parser("preview").add_subparsers(dest="action", required=True)
    pshow = preview.add_parser("show"); pshow.add_argument("project_id", type=int); pshow.add_argument("--version-id", type=int)
    generate = preview.add_parser("generate"); generate.add_argument("project_id", type=int); generate.add_argument("--request-id"); generate.add_argument("--expected-version", type=int)

    vstyles = sub.add_parser("visual-styles", help="单页视觉风格（visual_style_id）").add_subparsers(dest="action", required=True)
    vstyles.add_parser("list", help="列出视觉风格预设")
    theme = sub.add_parser("theme", help="主题配色 / 章节页模板（预览阶段）").add_subparsers(dest="action", required=True)
    tset = theme.add_parser("set"); tset.add_argument("project_id", type=int)
    for color in ("primary", "secondary", "accent", "text-color"):
        tset.add_argument(f"--{color}", help="#RRGGBB")
    tset.add_argument("--apply-section-template", action="store_true", help="应用最新章节页模板")
    _versioned(tset)
    layout = sub.add_parser("layout", help="查看叙事分析页面列表").add_subparsers(dest="action", required=True)
    lshow = layout.add_parser("show"); lshow.add_argument("project_id", type=int)
    pages = sub.add_parser("pages", help="逐页编辑：标题/正文/视觉风格/拆分/合并/重生成图片等").add_subparsers(dest="action", required=True)
    pedit = pages.add_parser("edit", help="修改本页标题、副标题、正文、讲稿、视觉风格或标题宽度")
    pedit.add_argument("project_id", type=int); pedit.add_argument("page_number", type=int)
    pedit.add_argument("--title"); pedit.add_argument("--subtitle"); pedit.add_argument("--content")
    pedit.add_argument("--content-file", type=Path); pedit.add_argument("--narrative")
    pedit.add_argument("--visual-style", help="visual_style_id，见 `sulaide visual-styles list`")
    pedit.add_argument("--title-width", type=float, help="标题区域宽度（px，画布 1600 宽，最小 240）")
    pedit.add_argument("--subtitle-width", type=float, help="副标题区域宽度（px）")
    _versioned(pedit)
    padd = pages.add_parser("add", help="新增页面"); padd.add_argument("project_id", type=int)
    padd.add_argument("--after", type=int, help="插入到第 N 页之后（默认末尾）"); padd.add_argument("--title"); padd.add_argument("--content")
    _versioned(padd)
    for name, help_ in (("delete", "删除页面"), ("duplicate", "复制页面"), ("merge", "合并到上一页（AI 重写标题）")):
        sp = pages.add_parser(name, help=help_); sp.add_argument("project_id", type=int); sp.add_argument("page_number", type=int)
        _versioned(sp)
        if name == "merge": _structure_wait(sp)
    pmove = pages.add_parser("move", help="上移/下移页面"); pmove.add_argument("project_id", type=int); pmove.add_argument("page_number", type=int)
    pmove.add_argument("direction", choices=("up", "down")); _versioned(pmove)
    psplit = pages.add_parser("split", help="在正文第 N 个字符处拆分为两页（AI 重写标题）")
    psplit.add_argument("project_id", type=int); psplit.add_argument("page_number", type=int)
    psplit.add_argument("--at", type=int, required=True, help="正文字符偏移，第二页从这里开始"); _versioned(psplit); _structure_wait(psplit)
    prean = pages.add_parser("reanalyze", help="单页重新分析（重写标题、副标题、正文和叙事）")
    prean.add_argument("project_id", type=int); prean.add_argument("page_number", type=int); prean.add_argument("--instruction")
    _versioned(prean)
    pregen = pages.add_parser("regenerate", help="重新生成本页图片（消耗积分）")
    pregen.add_argument("project_id", type=int); pregen.add_argument("page_number", type=int)
    pregen.add_argument("--prompt"); pregen.add_argument("--visual-style"); pregen.add_argument("--request-id")
    pimg = pages.add_parser("edit-image", help="按指令修改本页图片（消耗积分）")
    pimg.add_argument("project_id", type=int); pimg.add_argument("page_number", type=int)
    pimg.add_argument("--prompt", required=True); pimg.add_argument("--reference-image", type=Path); pimg.add_argument("--request-id")
    phist = pages.add_parser("images", help="查看本页图片历史版本"); phist.add_argument("project_id", type=int); phist.add_argument("slide_id")
    prest = pages.add_parser("restore-image", help="恢复本页的历史图片")
    prest.add_argument("project_id", type=int); prest.add_argument("slide_id")
    prest.add_argument("--source-version", type=int, required=True, help="images 输出里的 source_version_id")
    prest.add_argument("--version-id", type=int, required=True, help="当前 active 版本 ID"); prest.add_argument("--manifest-hash", required=True)
    prest.add_argument("--request-id")

    resources = sub.add_parser("resources", help="查看和下载项目资源库中的资源").add_subparsers(dest="action", required=True)
    resources_list = resources.add_parser("list", help="列出资源库中的资源版本")
    resources_list.add_argument("project_id", type=int)
    resources_list.add_argument("--resource-type", choices=("upload", "narrative_analysis", "generated_image", "export_pptx", "export_pdf"), help="按资源类型筛选")
    resources_list.add_argument("--page-number", type=int, help="页码，从 1 开始")
    resources_download = resources.add_parser("download", help="下载资源库中的一个资源版本")
    resources_download.add_argument("resource_version_id", type=int)
    resources_download.add_argument("--output", type=Path, required=True)

    export = sub.add_parser("export").add_subparsers(dest="action", required=True)
    export_start = export.add_parser("start"); export_start.add_argument("project_id", type=int); export_start.add_argument("--version-id", type=int, required=True); export_start.add_argument("--manifest-hash", required=True); export_start.add_argument("--mode", choices=("native", "text_editable", "full_editable"), default="native"); export_start.add_argument("--page-numbers", default=""); export_start.add_argument("--request-id")
    echeck = export.add_parser("check", help="导出前质量检查"); echeck.add_argument("project_id", type=int); echeck.add_argument("--version-id", type=int, required=True); echeck.add_argument("--manifest-hash", required=True)
    download = export.add_parser("download"); download.add_argument("project_id", type=int); download.add_argument("version_id", type=int); download.add_argument("manifest_hash"); download.add_argument("--run-id"); download.add_argument("--output", type=Path, required=True)

    operations = sub.add_parser("operations").add_subparsers(dest="action", required=True)
    op_show = operations.add_parser("show"); op_show.add_argument("operation_id")
    skills = sub.add_parser("skills", help="把四步法 skill 安装到本机编码 Agent").add_subparsers(dest="action", required=True)
    for action in ("install", "uninstall"):
        sp = skills.add_parser(action)
        sp.add_argument("--agent", action="append", help="目标 Agent，可重复；默认自动检测")
        sp.add_argument("--all", action="store_true", help="所有已知 Agent")
        if action == "install": sp.add_argument("--force", action="store_true", help="覆盖非 sulaide 安装的同名目录")
    skills.add_parser("update", help="更新已安装过的 Agent")
    skills.add_parser("list", help="查看检测到的 Agent 与安装状态")
    credits = sub.add_parser("credits", help="查询当前账户剩余积分")
    credits.add_argument("--human", action="store_true", help="输出一行中文摘要而不是 JSON")
    coupons = sub.add_parser("coupons", help="查询当前账户的卡券（只读）")
    coupons.add_argument("--status", choices=("available", "not_started", "used", "expired", "voided"))
    coupons.add_argument("--page", type=int, default=1)
    coupons.add_argument("--size", type=int, default=20)
    coupons.add_argument("--human", action="store_true", help="输出中文列表而不是 JSON")
    topup = sub.add_parser("topup", help="积分充值：列出套餐 / 生成支付宝付款链接并等待到账 / --web 打开网页充值页")
    topup.add_argument("action", nargs="?", choices=("packages",), help="packages：列出全部充值套餐")
    topup.add_argument("--package", type=int, help="套餐 ID（不填则列出可购买的套餐）")
    topup.add_argument("--open", action="store_true", help="在浏览器打开支付宝付款页")
    topup.add_argument("--qr", action="store_true", help="在终端打印付款链接二维码（需安装 qrcode）")
    topup.add_argument("--no-wait", action="store_true", help="只创建订单并输出付款链接，不等待支付结果")
    topup.add_argument("--timeout", type=float, default=900, help="等待支付的秒数（默认 900）")
    topup.add_argument("--status", metavar="ORDER_NO", help="查询某个充值订单的状态")
    topup.add_argument("--request-id")
    topup.add_argument("--web", action="store_true", help="只在浏览器打开官网充值页")
    topup.add_argument("--human", action="store_true", help="输出中文摘要而不是 JSON")
    packages = sub.add_parser("packages", help="列出全部积分充值套餐（同 `sulaide topup packages`）")
    packages.add_argument("--human", action="store_true", help="输出中文列表而不是 JSON")
    fb = sub.add_parser("feedback", aliases=["issue"], help="反馈问题：提交到速来得平台（自动脱敏，不公开）")
    fb.add_argument("--title")
    fb.add_argument("--body", "-m", help="问题描述")
    fb.add_argument("--type", choices=("bug", "feature", "question"), default="bug")
    fb.add_argument("--error", help="出错的命令或错误输出；传 - 从标准输入读取")
    fb.add_argument("--stdin", action="store_true", help="从标准输入读取错误输出")
    fb.add_argument("--keep-emails", action="store_true", help="不隐藏邮箱地址")
    fb.add_argument("--dry-run", action="store_true", help="只显示将要提交的内容，不提交")
    fb.add_argument("--list", action="store_true", help="查看自己提交过的反馈及处理状态")
    fb.add_argument("--page", type=int, default=1)
    fb.add_argument("--size", type=int, default=20)
    upd = sub.add_parser("update", help="通过 uv 升级 sulaide CLI，并刷新已安装的 skill")
    upd.add_argument("--check", action="store_true", help="只检查是否有新版本，不安装")
    upd.add_argument("--no-skills", action="store_true", help="升级后不刷新 skill")
    wait = sub.add_parser("wait"); wait.add_argument("operation_id"); wait.add_argument("--timeout", type=float, default=180)
    return parser


WEB_RECHARGE_PATH = "/app/credits"
TOPUP_POLL_INTERVAL = 3.0


def _is_alipay_url(url) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "alipay.com" or host.endswith(".alipay.com")
                                          or host == "alipaydev.com" or host.endswith(".alipaydev.com"))


def _print_qr(text: str) -> bool:
    try:
        import qrcode  # optional: uv tool install 'sulaide-cli[qr]'
    except ImportError:
        print("（未安装二维码依赖，安装时加 `--with qrcode` 即可启用终端二维码；也可直接打开链接，支付宝页面内自带扫码）", file=sys.stderr)
        return False
    qr = qrcode.QRCode(border=1)
    qr.add_data(text)
    qr.make(fit=True)
    qr.print_ascii(out=sys.stderr, invert=True)
    return True


def _packages_summary(result: dict) -> str:
    lines = ["可购买的积分套餐（用 `sulaide topup --package <ID>` 下单）："]
    for item in result.get("items") or []:
        extra = ""
        if item.get("original_price") and item.get("original_price") != item.get("price"):
            extra += f"（原价 ¥{item['original_price']}）"
        if item.get("promotion_label"):
            extra += f"，{item['promotion_label']}"
        if item.get("promotion_description"):
            extra += f"：{item['promotion_description']}"
        if item.get("purchasable") is False:
            extra += "（不可通过 CLI 购买）"
        lines.append(f"- [{item.get('id')}] {item.get('name')}：¥{item.get('price')} → {item.get('credit_amount')} 积分{extra}")
    if len(lines) == 1:
        lines.append("（暂无上架套餐）")
    return "\n".join(lines)


def _list_packages(client: "Client") -> dict:
    result = client.request("GET", "/topup/packages")
    if isinstance(result, dict):
        result.setdefault("how_to_buy", "sulaide topup --package <ID> --open")
    return result


def _topup(client: "Client", args) -> dict:
    if args.web:
        url = _base_url() + WEB_RECHARGE_PATH
        opened = webbrowser.open(url)
        return {"url": url, "opened": bool(opened), "message": "请在网页上登录后选择套餐并完成支付。"}
    if args.status:
        return client.request("GET", f"/topup/orders/{args.status}")
    if args.package is None:
        return _list_packages(client)
    key = f"topup:{args.package}"
    rid = _request_id(key, args.request_id)
    order = client.request("POST", "/topup/orders", json_body={"package_id": args.package, "request_id": rid})
    state = _read_state()
    state.pop(f"{key}:latest", None)  # next intentional run creates a new order
    _write_state(state)
    payment = order.get("payment") or {}
    pay_url = payment.get("pay_url")
    if order.get("status") == "paid" or not pay_url:
        return order
    if not _is_alipay_url(pay_url):
        raise ValueError("服务端返回的支付链接不是支付宝域名，已拒绝打开")
    print(f"订单号：{order.get('order_no')}，应付 ¥{order.get('payable_amount')}，到账 {order.get('credit_amount')} 积分", file=sys.stderr)
    print(f"请在浏览器打开以下支付宝链接完成付款（页面内可用支付宝 App 扫码），有效期至 {payment.get('expires_at')}：", file=sys.stderr)
    print(pay_url, file=sys.stderr)
    if args.qr:
        _print_qr(pay_url)
    if args.open:
        webbrowser.open(pay_url)
    if args.no_wait:
        return order
    deadline = time.monotonic() + args.timeout
    print("等待支付结果…（Ctrl+C 退出后可用 `sulaide topup --status <订单号>` 继续查询）", file=sys.stderr)
    while True:
        status = client.request("GET", f"/topup/orders/{order['order_no']}")
        if status.get("status") != "pending_payment":
            return status
        if time.monotonic() >= deadline:
            raise TimeoutError(f"在 {args.timeout:.0f} 秒内未确认支付，订单 {order['order_no']} 仍待支付；付款后可运行 `sulaide topup --status {order['order_no']}`")
        time.sleep(TOPUP_POLL_INTERVAL)


def _topup_summary(result: dict) -> str:
    if "items" in result and "order_no" not in result:
        return _packages_summary(result)
    if "url" in result:
        return f"充值页：{result['url']}" + ("（已在浏览器打开）" if result.get("opened") else "")
    status = result.get("status")
    if status == "paid":
        bal = result.get("balance") or {}
        return f"支付成功：订单 {result.get('order_no')}，到账 {result.get('credit_amount')} 积分；当前可用积分 {bal.get('available')}"
    return f"订单 {result.get('order_no')} 状态：{status}"


def _versioned(parser) -> None:
    parser.add_argument("--request-id", help="幂等键，仅用于重试同一条命令；不要在 add 与 duplicate 等不同页面写操作之间复用")
    parser.add_argument("--expected-version", type=int, help="预期的编辑版本 ID（layout show 输出）；省略则用当前版本")
    parser.add_argument("--expected-revision", type=int, help="预期的 manifest_revision；省略则用当前值")


def _structure_wait(parser) -> None:
    parser.add_argument("--no-wait", action="store_true", help="只启动标题任务，不等待并应用")
    parser.add_argument("--timeout", type=float, default=180)


def _body_key(body: dict) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def _write(client, key: str, method: str, path: str, body: dict, explicit_rid=None) -> dict:
    """Idempotent write: the request_id is reused only for the same command + body."""
    command = f"{key}:{_body_key(body)}"
    rid = _request_id(command, explicit_rid)
    result = client.request(method, path, json_body={"request_id": rid, **body})
    _remember_operation(command, rid, (result.get("operation") or {}).get("operation_id"))
    return result


def _version_body(args) -> dict:
    return {k: v for k, v in (("expected_presentation_version_id", getattr(args, "expected_version", None)),
                              ("expected_manifest_revision", getattr(args, "expected_revision", None))) if v is not None}


def _structure(client, args, kind: str) -> dict:
    base = f"/projects/{args.project_id}"
    body = {**_version_body(args), **({"split_offset": args.at} if kind == "split" else {})}
    started = _write(client, f"pages_{kind}:{args.project_id}:{args.page_number}", "POST",
                     f"{base}/pages/{args.page_number}/{kind}", body, args.request_id)
    if args.no_wait:
        return started
    run_id = started["run_id"]
    deadline = time.monotonic() + args.timeout
    while True:
        run = client.request("GET", f"{base}/structure-runs/{run_id}")
        if run.get("status") == "succeeded":
            break
        if run.get("status") in ("failed", "cancelled"):
            raise ApiError(409, {"reason": "TITLE_RUN_FAILED", "run": run})
        if time.monotonic() > deadline:
            raise ApiError(504, {"reason": "TITLE_RUN_TIMEOUT", "run_id": run_id,
                                 "hint": "稍后重新运行同一命令即可继续"})
        time.sleep(2)
    apply_body = {"run_id": run_id, "kind": kind, "page_number": args.page_number,
                  "expected_presentation_version_id": started.get("presentation_version_id"),
                  "expected_manifest_revision": started.get("manifest_revision"),
                  **({"split_offset": args.at} if kind == "split" else {})}
    return _write(client, f"pages_{kind}_apply:{args.project_id}", "POST",
                  f"{base}/structure-runs/{run_id}/apply", apply_body)


def _pages(client, args) -> dict:
    base = f"/projects/{args.project_id}"
    a = args.action
    if a == "images":
        return client.request("GET", f"{base}/pages/{args.slide_id}/image-versions")
    if a == "restore-image":
        return _write(client, f"image_restore:{args.project_id}:{args.slide_id}", "POST",
                      f"{base}/pages/{args.slide_id}/image-versions/restore",
                      {"source_version_id": args.source_version, "expected_presentation_version_id": args.version_id,
                       "expected_manifest_hash": args.manifest_hash}, args.request_id)
    if a in ("split", "merge"):
        return _structure(client, args, a)
    if a == "add":
        body = {**_version_body(args), **{k: v for k, v in (("after_page", args.after), ("title", args.title),
                                                             ("content", args.content)) if v is not None}}
        return _write(client, f"pages_add:{args.project_id}", "POST", f"{base}/pages", body, args.request_id)
    page = f"{base}/pages/{args.page_number}"
    key = f"pages_{a}:{args.project_id}:{args.page_number}"
    if a == "edit":
        content = args.content_file.read_text(encoding="utf-8") if args.content_file else args.content
        fields = {k: v for k, v in (("title", args.title), ("subtitle", args.subtitle), ("content", content),
                                    ("narrative", args.narrative), ("visual_style_id", args.visual_style),
                                    ("title_width", args.title_width), ("subtitle_width", args.subtitle_width))
                  if v is not None}
        if not fields: raise ValueError("没有要修改的字段（--title/--subtitle/--content/--narrative/--visual-style/--title-width/--subtitle-width）")
        return _write(client, key, "PATCH", page, {**_version_body(args), **fields}, args.request_id)
    if a in ("delete", "duplicate"):
        return _write(client, key, "POST", f"{page}/{a}", _version_body(args), args.request_id)
    if a == "move":
        return _write(client, key, "POST", f"{page}/move", {**_version_body(args), "direction": args.direction}, args.request_id)
    if a == "reanalyze":
        body = _version_body(args)
        if args.instruction:
            body["instruction"] = args.instruction
        return _write(client, key, "POST", f"{page}/reanalyze", body, args.request_id)
    if a == "regenerate":
        body = {k: v for k, v in (("prompt", args.prompt), ("visual_style_id", args.visual_style)) if v}
        return _write(client, key, "POST", f"{page}/regenerate", body, args.request_id)
    if a == "edit-image":
        body = {"prompt": args.prompt}
        if args.reference_image:
            import base64, mimetypes
            mime = mimetypes.guess_type(args.reference_image.name)[0] or "image/png"
            body["reference_image"] = f"data:{mime};base64," + base64.b64encode(args.reference_image.read_bytes()).decode()
        return _write(client, key, "POST", f"{page}/edit-image", body, args.request_id)
    raise ValueError(a)


def _theme(client, args) -> dict:
    colors = {k: v for k, v in (("primary", args.primary), ("secondary", args.secondary), ("accent", args.accent),
                                ("text_color", args.text_color)) if v}
    if not colors and not args.apply_section_template:
        raise ValueError("请至少指定一个颜色或 --apply-section-template")
    return _write(client, f"theme:{args.project_id}", "POST", f"/projects/{args.project_id}/theme",
                  {**_version_body(args), **colors, "apply_latest_section_template": args.apply_section_template},
                  args.request_id)


def run(args) -> dict:
    if args.area == "auth":
        return _auth_command(args)
    if args.area == "topup" and args.web:
        return _topup(None, args)
    if args.area in ("feedback", "issue"):
        from . import feedback
        return feedback.submit(args)
    if args.area == "update":
        from . import update
        return update.check() if args.check else update.update(skills=not args.no_skills)
    if args.area == "skills":
        from . import skills
        if args.action == "list": return skills.status()
        if args.action == "update": return skills.update()
        targets = skills.resolve_agents(args.agent, args.all)
        if args.action == "uninstall": return skills.uninstall(targets)
        return skills.install(targets, force=args.force)
    client = Client()
    if args.area == "projects":
        if args.action == "list": return client.request("GET", "/projects")
        if args.action == "show": return client.request("GET", f"/projects/{args.project_id}")
        rid = _request_id("project_create", args.request_id)
        body = {"request_id": rid, "title": args.title}
        if args.language: body["language"] = args.language
        result = client.request("POST", "/projects", json_body=body)
        _remember_operation("project_create", rid, (result.get("operation") or {}).get("operation_id"))
        return result
    if args.area == "styles":
        return client.request("GET", "/styles")
    if args.area == "visual-styles":
        return client.request("GET", "/visual-styles")
    if args.area == "layout":
        return client.request("GET", f"/projects/{args.project_id}/layout")
    if args.area == "pages":
        return _pages(client, args)
    if args.area == "theme":
        return _theme(client, args)
    if args.area == "export" and args.action == "check":
        return client.request("GET", f"/projects/{args.project_id}/export-check",
                              params={"version_id": args.version_id, "manifest_hash": args.manifest_hash})
    if args.area == "source":
        file_path = getattr(args, "file", None)
        if args.action == "upload":
            text = file_path.read_text(encoding="utf-8")
        else:
            text = args.text if args.text is not None else args.file.read_text(encoding="utf-8") if args.file else None
        if text is None: raise ValueError("Provide --text or --file")
        rid = _request_id(f"source_save:{args.project_id}", args.request_id)
        result = client.request("PUT", f"/projects/{args.project_id}/source", json_body={
            "request_id": rid, "content": text,
            "filename": str(file_path.name) if file_path else None,
            "expected_source_revision": args.expected_revision,
            **_source_options(args),
        })
        _remember_operation(f"source_save:{args.project_id}", rid, (result.get("operation") or {}).get("operation_id"))
        return result
    if args.area == "analysis":
        if args.page_count is not None and not 1 <= args.page_count <= 50:
            raise ValueError("--page-count 必须在 1–50 之间")
        rid = _request_id(f"analysis:{args.project_id}", args.request_id)
        result = client.request("POST", f"/projects/{args.project_id}/analysis", json_body={
            "request_id": rid, "page_count": args.page_count, "expected_source_revision": args.expected_revision,
            **({"structure_requirements": args.structure_requirements} if args.structure_requirements else {}),
        })
        _remember_operation(f"analysis:{args.project_id}", rid, (result.get("operation") or {}).get("operation_id"))
        return result
    if args.area == "preview":
        if args.action == "show": return client.request("GET", f"/projects/{args.project_id}/presentation", params={"version_id": args.version_id})
        rid = _request_id(f"preview:{args.project_id}", args.request_id)
        result = client.request("POST", f"/projects/{args.project_id}/preview/continue", json_body={
            "request_id": rid, "expected_presentation_version_id": args.expected_version,
        })
        _remember_operation(f"preview:{args.project_id}", rid, (result.get("operation") or {}).get("operation_id"))
        return result
    if args.area == "resources":
        if args.action == "list":
            params = {"project_id": args.project_id}
            if args.resource_type:
                params["resource_type"] = args.resource_type
            if args.page_number is not None:
                params["page_number"] = args.page_number
            return client.request("GET", "/resource-versions", params=params)
        destination = args.output.expanduser().resolve()
        if destination.exists(): raise FileExistsError(f"Refusing to overwrite {destination}")
        meta = client.request("GET", f"/resource-versions/{args.resource_version_id}/download")
        if not isinstance(meta, dict):
            raise ValueError("Resource download metadata was not an object")
        url = meta.get("redirect_url") or (meta.get("data") or {}).get("redirect_url")
        if not url:
            raise ValueError("Resource download link was not returned")
        if url.startswith("/"):
            url = _base_url() + url
        if httpx.URL(url).host == httpx.URL(_base_url()).host:
            response = client.http.get(url, follow_redirects=True)
        else:
            # Signed storage URLs live on another host: never send the API key there.
            with httpx.Client(timeout=httpx.Timeout(30, read=90), follow_redirects=True) as anonymous:
                response = anonymous.get(url)
        if response.is_error or "application/json" in response.headers.get("content-type", ""):
            raise ApiError(response.status_code, response.text)
        content = response.content
        if not content:
            raise ValueError("Downloaded resource is empty")
        temp = destination.with_name(destination.name + ".part")
        temp.write_bytes(content)
        temp.replace(destination)
        return {"path": str(destination), "size_bytes": len(content),
                "resource_version_id": args.resource_version_id, "filename": meta.get("filename") or str(args.resource_version_id)}
    if args.area == "export":
        if args.action == "start":
            rid = _request_id(f"export:{args.project_id}:{args.version_id}", args.request_id)
            result = client.request("POST", f"/projects/{args.project_id}/exports", json_body={
                "request_id": rid, "presentation_version_id": args.version_id,
                "manifest_hash": args.manifest_hash, "mode": args.mode,
                "page_numbers": [int(value) for value in args.page_numbers.split(",") if value.strip()],
            })
            _remember_operation(f"export:{args.project_id}:{args.version_id}", rid, (result.get("operation") or {}).get("operation_id"))
            return result
        destination = args.output.expanduser().resolve()
        if destination.exists(): raise FileExistsError(f"Refusing to overwrite {destination}")
        # native exports have no run_id: omit the param entirely (httpx would send `run_id=`
        # for None, which the server rejected with a 422).
        params = {"manifest_hash": args.manifest_hash}
        if args.run_id: params["run_id"] = args.run_id
        response = client.http.get(f"{client.base}/projects/{args.project_id}/exports/{args.version_id}/download",
            params=params)
        _check_download_response(response)
        temp = destination.with_name(destination.name + ".part")
        temp.write_bytes(response.content)
        temp.replace(destination)
        return {"path": str(destination), "size_bytes": len(response.content), "source_hash": response.headers.get("x-sulaide-source-hash")}
    if args.area == "packages" or (args.area == "topup" and args.action == "packages"):
        return _list_packages(client)
    if args.area == "topup": return _topup(client, args)
    if args.area == "credits": return client.request("GET", "/credits")
    if args.area == "coupons":
        params = {"page": args.page, "size": args.size}
        if args.status: params["status"] = args.status
        return client.request("GET", "/coupons", params=params)
    if args.area == "operations": return client.request("GET", f"/operations/{args.operation_id}")
    if args.area == "wait": return _wait(client, args.operation_id, args.timeout)
    raise ValueError("Unsupported command")


def main() -> None:
    if sys.argv[1:2] == ["--version"]:
        from .update import local_info, _label
        info = local_info()
        print(json.dumps(info) if "--json" in sys.argv[2:] else f"sulaide {_label(info)}")
        return
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(args)
        if args.area == "credits" and args.human:
            print(_credits_summary(result))
        elif args.area == "packages" and args.human:
            print(_packages_summary(result))
        elif args.area == "topup" and args.human:
            print(_topup_summary(result))
        elif args.area == "coupons" and args.human:
            print(_coupons_summary(result))
        else:
            _emit(result, json_mode=not args.pretty)
    except ApiError as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        reason = detail.get("reason") if isinstance(detail, dict) else None
        print(json.dumps({"error": {"http_status": exc.status, **detail,
            "retryable": detail.get("retryable", exc.status in {408, 429, 502, 503, 504}),
            "next_action": "query_operation" if exc.status == 202 else "review_request"}}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(4 if exc.status == 401 else 3 if exc.status == 409 else 2)
    except TimeoutError as exc:
        print(json.dumps({"error": {"category": "wait_timeout", "message": str(exc), "retryable": True, "next_action": "wait_again"}}), file=sys.stderr)
        raise SystemExit(5)
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        print(json.dumps({"error": {"category": "network_error", "message": str(exc),
            "retryable": True, "next_action": "reuse_request_id_or_query_operation"}}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(6)
    except (ValueError, OSError, httpx.HTTPError) as exc:
        print(json.dumps({"error": {"category": "client_error", "message": str(exc), "retryable": False}}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
