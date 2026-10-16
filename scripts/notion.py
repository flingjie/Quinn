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
            value = value.split("#", 1)[0].strip()
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
            f.write("# c\ninteraction: on\nnotion_notes_page_id: abc123   # Notes 容器页 id\nnotion_lookback_days: 7   # 最近 N 天日记\n")
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


if __name__ == "__main__":
    sys.exit(main())
