# Quinn 只读 Notion 日记接入 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Quinn 增加一个只读的 Notion 日记读取脚本，让 `quinn-explore` 能把最近一周日记当作「材料」接入探索流程。

**Architecture:** 单个确定性脚本 `scripts/notion.py`（标准库 urllib 直连 Notion REST，只 GET 页面/块，不碰数据库），沿用 Finch 的传输写法与 Quinn 的「脚本 + selftest」惯例。凭据 `NOTION_API_KEY` 读环境变量或仓库根 `.env`；`notes_page_id` / `lookback_days` 读 `workspace/config.md`。`quinn-explore` 经一份参考文件按需调用，不新增第 4 个 skill。

**Tech Stack:** Python 3 标准库（`urllib` / `argparse` / `json` / `datetime` / `tempfile`）；无第三方依赖。

## Global Constraints

- 只读：不写回 Notion、不建本地缓存/待同步队列/同步操作日志。
- 不碰 Notion 数据库（database），只读页面与块（page / block children）。
- 不 import Finch、不抽共享包。
- 无第三方 HTTP 依赖（标准库 `urllib` 即可）；无 pytest（用脚本自带 `selftest`，对齐 `workspace.py`）。
- Notion API 版本固定 `2022-06-28`；请求头 `Authorization: Bearer <key>`。
- 凭据与 page id 不进版本控制：`.env` 与 `workspace/config.md` 均为 gitignored。
- 「最近一周」按 block 的 `created_time` 过滤，不解析标题字符串。

---

## File Structure

| 文件 | 责任 | 动作 |
| --- | --- | --- |
| `scripts/notion.py` | 只读 Notion 传输 + 文本提取 + 命令 + 离线自检 | 新建 |
| `.gitignore` | 加 `.env` 忽略 | 修改 |
| `.env` | `NOTION_API_KEY`（gitignored，本地） | 新建（不提交） |
| `workspace/config.md` | `notion_notes_page_id` / `notion_lookback_days`（gitignored，本地） | 修改（不提交） |
| `skills/quinn-explore/references/notion-diary.md` | 何时调用、命令用法、材料归属 | 新建 |
| `skills/quinn-explore/SKILL.md` | 「输入」段加 Notion 日记来源 | 修改 |

---

### Task 1: `scripts/notion.py` 库核心（配置 + 传输 + 文本提取）

**Files:**
- Create: `scripts/notion.py`
- Modify: `.gitignore`（加 `.env`）
- Create（本地，不提交）: `.env`
- Modify（本地，不提交）: `workspace/config.md`

**Interfaces:**
- Consumes: 无（首个任务）。
- Produces: `NotionError(message, *, status_code, notion_code)`；`NotionClient(api_key=..., base_url=..., version=..., timeout=...)` 含方法 `list_all_block_children(block_id) -> list[dict]`；`load_env(path=ENV_PATH) -> None`；`load_workspace_config(path=CONFIG_PATH) -> dict`；`notion_config() -> tuple[str, str, int]`（`(api_key, notes_page_id, lookback_days)`）；`block_plain_text(block) -> str`；`flatten_blocks(blocks) -> str`；`user_region_text(children) -> str`；`_print_json(obj) -> None`。

- [ ] **Step 1: 写 `scripts/notion.py` 的库核心部分**

创建文件，内容为 docstring、imports、常量、`NotionError`、`NotionClient`、配置函数、文本提取函数、`_print_json`，以及一个只支持 `selftest` 的最小 `main` 和 `_selftest`：

```python
#!/usr/bin/env python3
"""Quinn 只读 Notion 日记读取脚本。

只做确定性的读取：从 Notes 容器递归发现月度页，收集日记 toggle 块，按
created_time 过滤最近 N 天，读某条的正文（默认剥掉 Finch 讨论记录区）。
不写回、不碰数据库、不建缓存。凭据 NOTION_API_KEY 优先读环境变量，未设置
时读仓库根 .env；notes_page_id 与 lookback_days 读 workspace/config.md。

用法：
    python3 scripts/notion.py list-diary [--days N]
    python3 scripts/notion.py read <block_id> [--with-discussion]
    python3 scripts/notion.py doctor
    python3 scripts/notion.py selftest

依赖：Python 3 标准库（urllib）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
REGION_FINCH = "Finch 讨论记录"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CONFIG_PATH = os.path.join(REPO_ROOT, "workspace", "config.md")
ENV_PATH = os.path.join(REPO_ROOT, ".env")


class NotionError(RuntimeError):
    """Notion 请求失败：携带 HTTP 状态码与 Notion 侧错误码。"""

    def __init__(self, message, *, status_code=None, notion_code=None):
        super().__init__(message)
        self.status_code = status_code
        self.notion_code = notion_code


class NotionClient:
    """Notion 只读 REST 客户端：列块 / 读块 children（薄封装，只 GET）。"""

    def __init__(self, *, api_key, base_url=NOTION_BASE_URL, version=NOTION_VERSION, timeout=30.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.version = version
        self.timeout = timeout

    def _request(self, method, path):
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": self.version,
        }
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise self._http_error(method, path, exc) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise self._network_error(method, path, exc) from exc

    def _http_error(self, method, path, exc):
        body = exc.read().decode("utf-8", "replace")
        notion_code = None
        try:
            parsed = json.loads(body)
            notion_code = parsed.get("code") if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            notion_code = None
        return NotionError(
            f"Notion {method} {path} failed ({exc.code}): {body[:200]}",
            status_code=exc.code,
            notion_code=notion_code,
        )

    def _network_error(self, method, path, exc):
        if isinstance(exc, TimeoutError):
            return NotionError(f"Notion {method} {path} timed out after {self.timeout:g}s")
        return NotionError(f"Notion {method} {path} network error: {exc.reason}")

    def list_all_block_children(self, block_id):
        blocks = []
        cursor = None
        while True:
            query = f"/blocks/{block_id}/children?page_size=100"
            if cursor:
                query += f"&start_cursor={quote(cursor)}"
            resp = self._request("GET", query)
            blocks.extend(resp.get("results", []))
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return blocks


def load_env(path=ENV_PATH):
    """读仓库根 .env 的 KEY=VALUE 行；已存在的环境变量优先，不覆盖。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_workspace_config(path=CONFIG_PATH):
    """读 workspace/config.md 的平铺 key: value 行，返回 dict；缺文件视为空。"""
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key:
                result[key] = value
    return result


def notion_config():
    """返回 (api_key, notes_page_id, lookback_days)；缺失时报 ValueError。"""
    load_env()
    cfg = load_workspace_config()
    api_key = os.environ.get("NOTION_API_KEY", "")
    notes_page_id = cfg.get("notion_notes_page_id", "")
    raw_days = cfg.get("notion_lookback_days", "7")
    try:
        lookback_days = int(raw_days)
    except ValueError:
        raise ValueError(f"notion_lookback_days 不是整数: {raw_days!r}")
    if not api_key:
        raise ValueError("缺少 NOTION_API_KEY（环境变量或 .env）")
    if not notes_page_id:
        raise ValueError("缺少 notion_notes_page_id（workspace/config.md）")
    return api_key, notes_page_id, lookback_days


def block_plain_text(block):
    """取块内纯文本（heading/paragraph/toggle/bulleted 等的 rich_text）。"""
    btype = block.get("type")
    if not btype:
        return ""
    value = block.get(btype) or {}
    rich = value.get("rich_text") or []
    return "".join(_rich_item_text(item) for item in rich)


def _rich_item_text(item):
    content = (item.get("text") or {}).get("content")
    if content:
        return content
    return item.get("plain_text") or ""


def flatten_blocks(blocks):
    """块 → 纯文本（空文本略过，用换行连接）。"""
    return "\n".join(text for block in blocks if (text := block_plain_text(block)))


def user_region_text(children):
    """用户区正文：取到「Finch 讨论记录」标记前的块，剥掉该区及其后内容。"""
    user_blocks = []
    for block in children:
        if block_plain_text(block).startswith(REGION_FINCH):
            break
        user_blocks.append(block)
    return flatten_blocks(user_blocks)


def _print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="notion.py", description="Quinn 只读 Notion 日记读取")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest", help="离线自检")
    args = parser.parse_args(argv)
    if args.cmd == "selftest":
        return _selftest()
    return 0


def _selftest():
    """离线自检（本任务：配置解析 + 文本剥除）。"""
    import tempfile

    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        cfg = os.path.join(tmp, "config.md")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write("# c\ninteraction: on\nnotion_notes_page_id: abc123\nnotion_lookback_days: 7\n")
        got = load_workspace_config(cfg)
        check("config parse", got.get("notion_notes_page_id") == "abc123" and got.get("notion_lookback_days") == "7")

        env = os.path.join(tmp, ".env")
        with open(env, "w", encoding="utf-8") as f:
            f.write("NOTION_SELFTEST_KEY=x\n")
        load_env(env)
        check("env load", os.environ.get("NOTION_SELFTEST_KEY") == "x")

    children = [
        {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "把AI当第二大脑"}}]}},
        {"type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": "Finch 讨论记录 #disc_x"}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "判断：..."}}]}},
    ]
    check("strip discussion", user_region_text(children) == "把AI当第二大脑")

    if failures:
        print(f"selftest 失败: {failures}")
        return 1
    print("selftest 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 跑自检，验证通过**

Run: `python3 scripts/notion.py selftest`
Expected: 输出 `selftest 通过`，退出码 0。

- [ ] **Step 3: 加 `.env` 到 `.gitignore`**

在 `.gitignore` 的「平台本地配置」段末尾加一行：

```gitignore
# 凭据（不进版本控制）
.env
```

- [ ] **Step 4: 本地配置（不提交）**

在 `workspace/config.md` 追加两行（把 `<NOTES_PAGE_ID>` 换成 Finch `finch.yaml` 里 `notion.notes_page_id` 的值，如 `1d44df9b-8964-805e-815c-ed927e3126fd`）：

```
notion_notes_page_id: <NOTES_PAGE_ID>   # Notes 容器页 id
notion_lookback_days: 7                 # 最近 N 天日记
```

新建 `.env`（内容为你的真实 token）：

```
NOTION_API_KEY=<你的 Notion token>
```

- [ ] **Step 5: 提交**

```bash
git add scripts/notion.py .gitignore
git commit -m "feat: 新增 notion.py 只读库核心（配置/传输/文本）与 .env 忽略"
```

---

### Task 2: 命令层（discover / list-diary / read / doctor + 完整自检）

**Files:**
- Modify: `scripts/notion.py`（加命令函数、改写 `main` 与 `_selftest`）

**Interfaces:**
- Consumes: `NotionClient.list_all_block_children`、`block_plain_text`、`flatten_blocks`、`user_region_text`、`notion_config`、`NotionError`、`_print_json`（Task 1）。
- Produces: `discover_page_ids(client, notes_page_id) -> list[str]`；`list_diary(client, notes_page_id, days, now=None) -> list[dict]`（每项含 `block_id`/`title`/`created_at`/`page_id`/`url`）；`read_entry(client, block_id, with_discussion=False) -> str`；`doctor(client, notes_page_id) -> dict`；`main` 支持 `list-diary`/`read`/`doctor`/`selftest`。

- [ ] **Step 1: 在 `main` 之前加命令函数**

在 `_print_json` 之后、`main` 之前插入：

```python
def discover_page_ids(client, notes_page_id):
    """递归发现 notes_page_id 下所有 child_page（年份页 + 月度页）。"""
    seen = set()
    queue = [notes_page_id]
    pages = []
    while queue:
        page_id = queue.pop(0)
        if page_id in seen:
            continue
        seen.add(page_id)
        for block in client.list_all_block_children(page_id):
            if block.get("type") != "child_page":
                continue
            child_id = block.get("id")
            if child_id and child_id not in seen:
                pages.append(child_id)
                queue.append(child_id)
    return pages


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def list_diary(client, notes_page_id, days, now=None):
    """收集所有日记 toggle 块，按 created_time 过滤最近 days 天，输出列表。"""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    entries = []
    for page_id in discover_page_ids(client, notes_page_id):
        for block in client.list_all_block_children(page_id):
            if block.get("type") != "toggle":
                continue
            created = _parse_iso(block.get("created_time"))
            if created is None or created < cutoff:
                continue
            entries.append({
                "block_id": block.get("id"),
                "title": block_plain_text(block),
                "created_at": block.get("created_time", ""),
                "page_id": page_id,
                "url": f"https://www.notion.so/{page_id}",
            })
    entries.sort(key=lambda e: e["created_at"])
    return entries


def read_entry(client, block_id, with_discussion=False):
    """读一条日记的正文；默认剥掉 Finch 讨论记录区。"""
    children = client.list_all_block_children(block_id)
    if with_discussion:
        return flatten_blocks(children)
    return user_region_text(children)


def doctor(client, notes_page_id):
    """只读核对 notes_page_id 可访问性，返回发现的页面数。"""
    pages = discover_page_ids(client, notes_page_id)
    return {"ok": True, "notes_page_id": notes_page_id, "pages": len(pages)}
```

- [ ] **Step 2: 改写 `main`，接入四个命令**

把现有 `main` 整个替换为：

```python
def main(argv=None):
    parser = argparse.ArgumentParser(prog="notion.py", description="Quinn 只读 Notion 日记读取")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list-diary", help="列出最近 N 天日记 toggle 块（JSON）")
    p.add_argument("--days", type=int, default=None, help="覆盖 config 的 lookback 天数")

    p = sub.add_parser("read", help="读一条日记正文（纯文本）")
    p.add_argument("block_id")
    p.add_argument("--with-discussion", action="store_true", help="包含 Finch 讨论记录区")

    sub.add_parser("doctor", help="核对 Notes 容器可访问性（只读）")
    sub.add_parser("selftest", help="离线自检（发现/过滤/剥除）")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "selftest":
            return _selftest()
        api_key, notes_page_id, lookback_days = notion_config()
        client = NotionClient(api_key=api_key)
        if args.cmd == "list-diary":
            days = args.days if args.days is not None else lookback_days
            _print_json(list_diary(client, notes_page_id, days))
        elif args.cmd == "read":
            print(read_entry(client, args.block_id, args.with_discussion))
        elif args.cmd == "doctor":
            _print_json(doctor(client, notes_page_id))
    except (ValueError, NotionError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    return 0
```

- [ ] **Step 3: 改写 `_selftest`，加 FakeClient 校验发现/过滤/剥除**

把现有 `_selftest` 整个替换为：

```python
def _selftest():
    """离线自检：config 解析 + 文本剥除 + FakeClient 发现/过滤。"""
    import tempfile

    class FakeClient:
        def __init__(self, pages):
            self.pages = pages

        def list_all_block_children(self, block_id):
            return self.pages.get(block_id, [])

    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        cfg = os.path.join(tmp, "config.md")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write("# c\ninteraction: on\nnotion_notes_page_id: abc123\nnotion_lookback_days: 7\n")
        got = load_workspace_config(cfg)
        check("config parse", got.get("notion_notes_page_id") == "abc123" and got.get("notion_lookback_days") == "7")

        env = os.path.join(tmp, ".env")
        with open(env, "w", encoding="utf-8") as f:
            f.write("NOTION_SELFTEST_KEY=x\n")
        load_env(env)
        check("env load", os.environ.get("NOTION_SELFTEST_KEY") == "x")

    pages = {
        "notes": [
            {"id": "year", "type": "child_page", "child_page": {"title": "2024"}},
            {"id": "m10", "type": "child_page", "child_page": {"title": "2026.10"}},
        ],
        "year": [],
        "m10": [
            {"id": "b1", "type": "toggle",
             "toggle": {"rich_text": [{"text": {"content": "10月9日 主动权"}}]},
             "created_time": "2026-10-09T02:35:00.000Z"},
            {"id": "b2", "type": "toggle",
             "toggle": {"rich_text": [{"text": {"content": "10月16日 软件闭环"}}]},
             "created_time": "2026-10-16T00:00:00.000Z"},
            {"id": "b3", "type": "toggle",
             "toggle": {"rich_text": [{"text": {"content": "9月1日 旧"}}]},
             "created_time": "2026-09-01T00:00:00.000Z"},
        ],
        "b1": [
            {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "把AI当第二大脑"}}]}},
            {"type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": "Finch 讨论记录 #disc_x"}}]}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "判断：..."}}]}},
        ],
        "b2": [
            {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "软件闭环正文"}}]}},
        ],
    }
    client = FakeClient(pages)
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)

    check("discover", discover_page_ids(client, "notes") == ["year", "m10"])
    check("list filter", [e["block_id"] for e in list_diary(client, "notes", 7, now)] == ["b1", "b2"])
    check("read strip", read_entry(client, "b1") == "把AI当第二大脑")
    check("read with discussion", "Finch 讨论记录" in read_entry(client, "b1", with_discussion=True))
    check("doctor", doctor(client, "notes")["pages"] == 2)

    if failures:
        print(f"selftest 失败: {failures}")
        return 1
    print("selftest 通过")
    return 0
```

- [ ] **Step 4: 跑自检，验证通过**

Run: `python3 scripts/notion.py selftest`
Expected: `selftest 通过`。

- [ ] **Step 5: 提交**

```bash
git add scripts/notion.py
git commit -m "feat: 新增 notion.py list-diary/read/doctor 命令与离线自检"
```

---

### Task 3: 真实冒烟（list-diary + read 对真实 Notion）

**Files:**
- 无新建/修改（除非冒烟暴露 bug 需修）。

**Interfaces:**
- Consumes: Task 2 的 `main` 全量命令；本地 `.env` 与 `workspace/config.md` 已配好（Task 1 Step 4）。

- [ ] **Step 1: 核对配置可访问**

Run: `python3 scripts/notion.py doctor`
Expected: 输出 JSON，`"ok": true`，`"pages"` 为大于 0 的整数（至少含最近月度页）。

- [ ] **Step 2: 列最近一周日记**

Run: `python3 scripts/notion.py list-diary --days 7`
Expected: JSON 列表，含 10/9–10/16 的 6 条（标题形如「10月9日 主动权」…「10月16日 软件闭环」），每条含 `block_id`/`title`/`created_at`/`page_id`/`url`。

- [ ] **Step 3: 读一条，验证讨论区被剥掉**

取 Step 2 里「10月9日 主动权」的 `block_id`，运行：

Run: `python3 scripts/notion.py read <block_id>`
Expected: 只输出用户原始正文，**不含**「Finch 讨论记录」字样。

再运行：

Run: `python3 scripts/notion.py read <block_id> --with-discussion`
Expected: 输出含「Finch 讨论记录」区。

- [ ] **Step 4: 回归**

Run: `python3 scripts/workspace.py selftest`
Expected: `selftest 通过`（确认未破坏现有写入脚本）。

- [ ] **Step 5: 提交（仅当冒烟暴露了需要修的 bug）**

```bash
git add scripts/notion.py
git commit -m "fix: 修正 notion.py 冒烟发现的问题"
```

若无需修改，跳过本步。

---

### Task 4: `quinn-explore` 接入（参考文件 + SKILL.md）

**Files:**
- Create: `skills/quinn-explore/references/notion-diary.md`
- Modify: `skills/quinn-explore/SKILL.md`

**Interfaces:**
- Consumes: Task 2 的命令接口（`list-diary` / `read` / `doctor`）。
- Produces: 无代码接口；产出一份可被 explore 按需加载的参考文件，与 SKILL.md 的一处输入来源提示。

- [ ] **Step 1: 新建参考文件**

创建 `skills/quinn-explore/references/notion-diary.md`：

```markdown
# Notion 日记材料（只读）

用户把日记存在 Notion（Notes 容器 → 月度页 → toggle 块，标题「M月D日 + 主题」）。
Quinn 只读日记作为探索「材料」，不写回。

## 何时用

用户说「看最近一周日记」「聊聊这条日记」「从日记里找点东西探索」等，把日记当材料时。

## 用法

```bash
# 列出最近 N 天日记（JSON；--days 覆盖 config 的 notion_lookback_days）
python3 scripts/notion.py list-diary --days 7

# 读某条正文（默认剥掉 Finch 讨论记录区；--with-discussion 才带上）
python3 scripts/notion.py read <block_id>

# 核对 Notes 容器可访问性（只读）
python3 scripts/notion.py doctor
```

- 凭据 `NOTION_API_KEY` 读环境变量或仓库根 `.env`；`notes_page_id` / `lookback_days` 读 `workspace/config.md`。
- `list-diary` 返回字段：`block_id`、`title`、`created_at`、`page_id`、`url`。

## 材料归属

- 日记条目是「材料」，session 正文记录 `block_id + 标题 + url` 作为来源；不把日记内容默认标成已证实事实（用户自述）。
- 结论仍由 synthesize 写 `workspace/sessions/`，不写回 Notion。
```

- [ ] **Step 2: 在 SKILL.md 的「输入」段加 Notion 日记来源**

在 `skills/quinn-explore/SKILL.md` 的「输入」段第一句末尾追加一句（把「用户困惑、项目问题、链接，或会话内异常现象」这句后面补上）：

原文（定位用）：
```
用户困惑、项目问题、链接，或会话内异常现象；可选已有 session / research 引用。有链接时先读内容，不凭标题推断。有研究记录时先 `python3 scripts/workspace.py read <id>`。
```

改为：
```
用户困惑、项目问题、链接，或会话内异常现象；可选已有 session / research 引用。用户把 Notion 日记当材料时按 `references/notion-diary.md` 调用读取。有链接时先读内容，不凭标题推断。有研究记录时先 `python3 scripts/workspace.py read <id>`。
```

- [ ] **Step 3: 在 SKILL.md 顶部参考列表加一行**

把第 10 行的参考文件枚举末尾补上 `notion-diary.md`：

原文（定位用）：
```
……导师式判断、建议与决定性问题见 `references/mentor-interaction.md`；迁移练习（举一反三，可选、用户发起）见 `references/transfer-practice.md`。
```

改为：
```
……导师式判断、建议与决定性问题见 `references/mentor-interaction.md`；迁移练习（举一反三，可选、用户发起）见 `references/transfer-practice.md`；Notion 日记材料见 `references/notion-diary.md`。
```

- [ ] **Step 4: 提交**

```bash
git add skills/quinn-explore/references/notion-diary.md skills/quinn-explore/SKILL.md
git commit -m "feat: quinn-explore 接入 Notion 日记材料"
```

---

## Self-Review

**Spec 覆盖：**
- §5.1 `scripts/notion.py`（list-diary/read/doctor/selftest）→ Task 1 + Task 2。✅
- §5.2 配置（`.env` + `config.md`）→ Task 1 Step 3–4。✅
- §5.3 `quinn-explore` 接入（reference + SKILL.md）→ Task 4。✅
- §7 测试（selftest + 真实冒烟 + workspace 回归）→ Task 2 Step 4 + Task 3。✅
- §6 明确不做（不写回/不碰数据库/不 import Finch）→ Global Constraints。✅

**占位符扫描：** 无 TBD/TODO；`<NOTES_PAGE_ID>` 与 `<你的 Notion token>` 是 Task 1 Step 4 里用户本地填写的真实值，属预期占位（gitignored 文件内容），不是计划缺漏。

**类型一致性：** `NotionClient.list_all_block_children(block_id)`、`block_plain_text`、`flatten_blocks`、`user_region_text`、`notion_config` 在 Task 1 定义、Task 2 消费，签名一致；`list_diary` 返回项字段名（`block_id`/`title`/`created_at`/`page_id`/`url`）在 Task 2 与 Task 4 参考文件一致。
