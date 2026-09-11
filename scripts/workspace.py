#!/usr/bin/env python3
"""Quinn workspace 文件操作脚本。

只做确定性的文件操作：创建、读取、查找、版本化更新与校验。不做策略分析、
自动评分、模型调度或流程编排（语义关联由 Agent 判断，关键写入约束由代码校验）。

记录格式：`workspace/<kind>/<id>.md`，YAML frontmatter + Markdown 正文。
字段约定见 `shared/contracts.md`（唯一真源）。

用法：
    python3 scripts/workspace.py create <kind> [payload]
    python3 scripts/workspace.py read <id>
    python3 scripts/workspace.py update <id> <revision> [payload]
    python3 scripts/workspace.py find <query> [kind]
    python3 scripts/workspace.py validate
    python3 scripts/workspace.py selftest

payload 为 YAML/JSON 文件路径（`-` 或省略则读 stdin）。payload 中保留键 `body`
为 Markdown 正文，其余键写入 frontmatter。`update` 时其余键改 frontmatter、
`body` 键改正文（省略 `body` 保留原正文）；省略整个 payload 则不修改任何字段。

依赖：Python 3 标准库 + PyYAML（`pip install pyyaml`）。
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    import fcntl
except ImportError:  # pragma: no cover - 非 Unix 平台退化
    fcntl = None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "workspace"))
LOCK_PATH = os.path.join(WORKSPACE_ROOT, ".lock")

KINDS = ("topics", "research", "discussions", "insights", "sessions")
SCHEMA_VERSION = "1"

ATTRIBUTIONS = {"source_author", "assistant", "user"}
USER_STANCES = {"accepted", "partial", "withheld", "rejected", "unexpressed"}
EVIDENCE_RELATIONS = {"supports", "contradicts", "limits", "inconclusive"}
OPEN_QUESTION_STATUSES = {"exploring", "waiting", "settled"}
SESSION_STATUSES = {"active", "paused", "completed", "save_failed"}
ACCESS_STATUSES = {"ok", "partial", "failed"}

# 脚本自管的公共字段，payload 不得提供
RESERVED_FIELDS = {"id", "schema_version", "revision", "created_at", "updated_at"}

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class RevisionConflict(Exception):
    """版本冲突：当前 revision 与期望值不符，需重读并合并。"""


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _kind_dir(kind: str) -> str:
    return os.path.join(WORKSPACE_ROOT, kind)


def _check_id(record_id: str) -> str:
    if not isinstance(record_id, str) or not _ID_RE.match(record_id):
        raise ValueError(f"非法记录 ID: {record_id!r}")
    return record_id


def _parse_structured(text: str):
    """解析 YAML（JSON 是其子集）；PyYAML 缺失时退回 JSON。"""
    if yaml is not None:
        return yaml.safe_load(text)
    return json.loads(text)


def _dump_structured(obj) -> str:
    if yaml is not None:
        return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _parse_file(text: str):
    """拆出 (frontmatter dict, body)；无 frontmatter 时返回 (None, text)。"""
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text
    fm_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    fm = _parse_structured(fm_text) if fm_text.strip() else {}
    return fm, body


def _serialize(fm: dict, body: str) -> str:
    parts = ["---", _dump_structured(fm).rstrip("\n"), "---"]
    if body:
        parts.append(body.rstrip("\n"))
    return "\n".join(parts) + "\n"


def _record_path(record_id: str):
    """返回 (kind, path)，不存在时返回 (None, None)。"""
    for kind in KINDS:
        p = os.path.join(_kind_dir(kind), record_id + ".md")
        if os.path.exists(p):
            return kind, p
    return None, None


def _evidence_refs(fm: dict) -> list[dict]:
    """收集 evidence_refs 与 history[].evidence_refs 中的证据引用条目。"""
    refs: list[dict] = []
    ev = fm.get("evidence_refs") or []
    if isinstance(ev, list):
        refs += [e for e in ev if isinstance(e, dict)]
    for h in fm.get("history") or []:
        if isinstance(h, dict):
            hev = h.get("evidence_refs") or []
            if isinstance(hev, list):
                refs += [e for e in hev if isinstance(e, dict)]
    return refs


def _referenced_ids(fm: dict) -> set[str]:
    """收集 frontmatter 引用的记录 ID（topic/record/research/证据）。"""
    refs: set[str] = set()
    for field in ("topic_ids", "record_ids", "research_ids"):
        v = fm.get(field) or []
        if isinstance(v, list):
            refs.update(x for x in v if isinstance(x, str))
    for ref in _evidence_refs(fm):
        if ref.get("record_id"):
            refs.add(ref["record_id"])
    return refs


def _check_references(fm: dict) -> None:
    """写约束：不得引用尚不存在的记录（引用记录先落盘，再写引用方）。"""
    for ref in sorted(_referenced_ids(fm)):
        if not _record_path(ref)[0]:
            raise ValueError(f"引用不存在的记录 {ref!r}（先落盘该记录，再引用）")


@contextlib.contextmanager
def _locked():
    """工作区级写锁，串行化"版本检查→替换"区间。"""
    if fcntl is None:  # pragma: no cover
        yield
        return
    os.makedirs(WORKSPACE_ROOT, exist_ok=True)
    with open(LOCK_PATH, "a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _atomic_write(path: str, text: str) -> None:
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "." + os.path.basename(path) + f".{uuid.uuid4().hex[:8]}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _collect_issues(fm: dict, kind: str) -> list[str]:
    """对单个 frontmatter 做枚举与归属校验，返回问题列表（无记录前缀）。"""
    issues: list[str] = []
    attr = fm.get("attribution")
    if attr is not None and attr not in ATTRIBUTIONS:
        issues.append(f"非法 attribution: {attr!r}（可选 {sorted(ATTRIBUTIONS)}）")
    stance = fm.get("user_stance")
    if stance is not None and stance not in USER_STANCES:
        issues.append(f"非法 user_stance: {stance!r}（可选 {sorted(USER_STANCES)}）")
    if stance in ("accepted", "partial", "withheld", "rejected"):
        history = fm.get("history") or []
        if not any(isinstance(h, dict) and h.get("user_quote") for h in history):
            issues.append(f"user_stance={stance} 但 history 缺少 user_quote（表态需原话依据，防默认接受）")
    if kind == "sessions":
        status = fm.get("status")
        if status is not None and status not in SESSION_STATUSES:
            issues.append(f"非法 status: {status!r}（可选 {sorted(SESSION_STATUSES)}）")
    for oq in fm.get("open_questions") or []:
        if isinstance(oq, dict):
            st = oq.get("status")
            if st is not None and st not in OPEN_QUESTION_STATUSES:
                issues.append(f"非法 open_question.status: {st!r}（可选 {sorted(OPEN_QUESTION_STATUSES)}）")
    for s in fm.get("sources") or []:
        if isinstance(s, dict):
            acc = s.get("access_status")
            if acc is not None and acc not in ACCESS_STATUSES:
                issues.append(f"非法 access_status: {acc!r}（可选 {sorted(ACCESS_STATUSES)}）")
    for ref in _evidence_refs(fm):
        if "relation" in ref and ref["relation"] not in EVIDENCE_RELATIONS:
            issues.append(f"非法 evidence relation: {ref['relation']!r}（可选 {sorted(EVIDENCE_RELATIONS)}）")
    return issues


def _validate_frontmatter(fm: dict, kind: str) -> None:
    issues = _collect_issues(fm, kind)
    if issues:
        raise ValueError("；".join(issues))


# --------------------------------------------------------------------------- #
# 公开接口（对应 shared/contracts.md §9）
# --------------------------------------------------------------------------- #


def create_record(kind: str, payload: dict | None = None, body: str = "") -> str:
    """校验、分配 ID、创建文件，返回新记录 ID。"""
    if kind not in KINDS:
        raise ValueError(f"未知记录类型: {kind!r}（可选 {KINDS}）")
    payload = dict(payload or {})
    for key in RESERVED_FIELDS:
        if key in payload:
            raise ValueError(f"字段 {key!r} 由脚本管理，不可在 payload 中提供")
    now = _now()
    fm = {
        "id": uuid.uuid4().hex,
        "schema_version": SCHEMA_VERSION,
        "revision": 1,
        "created_at": now,
        "updated_at": now,
    }
    fm.update(payload)
    _validate_frontmatter(fm, kind)
    _check_references(fm)
    path = os.path.join(_kind_dir(kind), fm["id"] + ".md")
    with _locked():
        _atomic_write(path, _serialize(fm, body))
    return fm["id"]


def read_record(record_id: str) -> dict:
    """读取并返回 id、kind、path、revision、frontmatter、body。"""
    _check_id(record_id)
    kind, path = _record_path(record_id)
    if path is None:
        raise FileNotFoundError(f"记录 {record_id} 不存在")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    fm, body = _parse_file(text)
    if not isinstance(fm, dict):
        raise ValueError(f"记录 {record_id} 缺少或损坏 frontmatter")
    return {
        "id": record_id,
        "kind": kind,
        "path": path,
        "revision": fm.get("revision"),
        "frontmatter": fm,
        "body": body,
    }


def update_record(record_id: str, expected_revision: int, payload: dict | None = None, body: str | None = None) -> int:
    """校验版本、原子替换、递增 revision，返回新 revision。"""
    _check_id(record_id)
    payload = dict(payload or {})
    for key in RESERVED_FIELDS:
        if key in payload:
            raise ValueError(f"字段 {key!r} 由脚本管理，不可在 payload 中提供")
    with _locked():
        cur = read_record(record_id)
        if cur["revision"] != expected_revision:
            raise RevisionConflict(
                f"版本冲突：记录 {record_id} 当前 revision={cur['revision']}，期望 {expected_revision}"
            )
        fm = dict(cur["frontmatter"])
        new_body = body if body is not None else cur["body"]
        fm.update(payload)
        fm["revision"] = cur["revision"] + 1
        fm["updated_at"] = _now()
        _validate_frontmatter(fm, cur["kind"])
        _check_references(fm)
        _atomic_write(cur["path"], _serialize(fm, new_body))
    return fm["revision"]


def find_records(query: str, kind: str | None = None) -> list[dict]:
    """元数据及正文全文查找候选，返回 [{id, kind, title, path}]。"""
    if kind is not None and kind not in KINDS:
        raise ValueError(f"未知记录类型: {kind!r}（可选 {KINDS}）")
    kinds = [kind] if kind else list(KINDS)
    q = (query or "").strip().lower()
    results = []
    for k in kinds:
        d = _kind_dir(k)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            p = os.path.join(d, name)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            if q and q not in text.lower():
                continue
            fm, _ = _parse_file(text)
            title = ""
            if isinstance(fm, dict):
                title = fm.get("title") or fm.get("question") or ""
            results.append({"id": name[:-3], "kind": k, "title": title, "path": p})
    return results


def validate_workspace() -> dict:
    """检查结构、引用完整性与归属约束，返回 {issues, summary}。"""
    issues: list[str] = []
    ids: dict[str, str] = {}
    for kind in KINDS:
        d = _kind_dir(kind)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            record_id = name[:-3]
            p = os.path.join(d, name)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read()
            except OSError as e:
                issues.append(f"[{kind}/{record_id}] 读取失败: {e}")
                continue
            fm, _ = _parse_file(text)
            if not isinstance(fm, dict):
                issues.append(f"[{kind}/{record_id}] frontmatter 缺失或非映射")
                continue
            if record_id in ids:
                issues.append(f"[{kind}/{record_id}] 重复 ID（同一 id 出现在多个 kind，引用无法定位）")
            ids[record_id] = kind
            if fm.get("id") != record_id:
                issues.append(f"[{kind}/{record_id}] id 与文件名不一致")
            for field in RESERVED_FIELDS:
                if field not in fm:
                    issues.append(f"[{kind}/{record_id}] 缺少公共字段 {field}")
            if not isinstance(fm.get("revision"), int) or fm.get("revision", 0) < 1:
                issues.append(f"[{kind}/{record_id}] revision 非法")
            for msg in _collect_issues(fm, kind):
                issues.append(f"[{kind}/{record_id}] {msg}")
    # 引用完整性
    for record_id, kind in ids.items():
        _, p = _record_path(record_id)
        with open(p, "r", encoding="utf-8") as f:
            fm, _ = _parse_file(f.read())
        plain: list[str] = []
        for field in ("topic_ids", "record_ids", "research_ids"):
            v = fm.get(field) or []
            if isinstance(v, list):
                plain += [x for x in v if isinstance(x, str)]
        for r in plain:
            if r not in ids:
                issues.append(f"[{kind}/{record_id}] 引用不存在的记录 {r}")
        for e in _evidence_refs(fm):
            rid = e.get("record_id")
            if not rid:
                continue
            if rid not in ids:
                issues.append(f"[{kind}/{record_id}] 证据引用不存在的记录 {rid}")
            elif ids.get(rid) != "research":
                issues.append(f"[{kind}/{record_id}] 证据引用 {rid} 不是 research 记录（实际 {ids.get(rid)}）")
    return {"issues": issues, "summary": {"records": len(ids), "issues": len(issues)}}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _load_payload(src):
    """返回 (payload_dict, body)。src 为 None/'-' 时读 stdin。"""
    if src in (None, "-"):
        text = sys.stdin.read()
    else:
        with open(src, "r", encoding="utf-8") as f:
            text = f.read()
    data = _parse_structured(text)
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        raise ValueError("payload 必须是映射（object），可含保留键 body 作为正文")
    body = data.pop("body", None)
    body = None if body is None else str(body)
    return data, body


def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="workspace.py", description="Quinn 工作区文件操作")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create", help="创建记录，打印新记录 ID")
    p.add_argument("kind", choices=KINDS)
    p.add_argument("payload", nargs="?")

    p = sub.add_parser("read", help="读取记录")
    p.add_argument("id")

    p = sub.add_parser("update", help="版本化更新记录")
    p.add_argument("id")
    p.add_argument("revision", type=int)
    p.add_argument("payload", nargs="?")

    p = sub.add_parser("find", help="全文查找记录")
    p.add_argument("query")
    p.add_argument("kind", nargs="?", choices=KINDS)

    sub.add_parser("validate", help="校验工作区结构、引用与归属")
    sub.add_parser("selftest", help="运行自检（创建/读/更新/冲突/校验）")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "create":
            payload, body = _load_payload(args.payload)
            record_id = create_record(args.kind, payload, body)
            _print_json({"id": record_id, "kind": args.kind, "revision": 1})
        elif args.cmd == "read":
            _print_json(read_record(args.id))
        elif args.cmd == "update":
            payload, body = _load_payload(args.payload) if args.payload else ({}, None)
            new_rev = update_record(args.id, args.revision, payload, body)
            _print_json({"id": args.id, "revision": new_rev})
        elif args.cmd == "find":
            _print_json(find_records(args.query, args.kind))
        elif args.cmd == "validate":
            _print_json(validate_workspace())
        elif args.cmd == "selftest":
            return _selftest()
    except (ValueError, FileNotFoundError, RevisionConflict, OSError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    return 0


def _selftest() -> int:
    """临时记录自检，验证后清理。"""
    import shutil

    created: list[str] = []
    failures: list[str] = []

    def check(name, cond):
        if not cond:
            failures.append(name)
        else:
            print(f"  ✓ {name}")

    print("selftest:")
    try:
        topic_id = create_record("topics", {"title": "自检专题", "aliases": ["selftest"], "scope": "临时", "record_ids": [], "summary": ""}, "自检正文")
        created.append(topic_id)
        check("create topics", topic_id)

        research_id = create_record(
            "research",
            {"question": "自检研究问题", "topic_ids": [topic_id], "sources": [], "claims": [], "disagreements": [], "unknowns": [], "coverage": "临时"},
            "研究正文",
        )
        created.append(research_id)
        check("create research", research_id)

        discussion_id = create_record(
            "discussions",
            {"question": "自检讨论", "research_ids": [research_id], "turns": [], "explanations": [], "methods_used": [], "opportunities": []},
            "讨论正文",
        )
        created.append(discussion_id)
        check("create discussions", discussion_id)

        insight_id = create_record(
            "insights",
            {
                "question": "自检认识",
                "explanation": "临时解释",
                "attribution": "assistant",
                "user_stance": "unexpressed",
                "evidence_refs": [{"record_id": research_id, "source_id": "s1"}],
                "boundaries": "临时",
                "open_questions": [],
                "history": [],
            },
            "认识正文",
        )
        created.append(insight_id)
        check("create insights", insight_id)

        session_id = create_record(
            "sessions", {"mode": "research", "topic_ids": [topic_id], "record_ids": [research_id], "status": "active", "next_step": "自检"}
        )
        created.append(session_id)
        check("create sessions", session_id)

        rec = read_record(research_id)
        check("read_record", rec["revision"] == 1 and rec["body"] == "研究正文")

        new_rev = update_record(research_id, 1, {"coverage": "已更新"}, "研究正文 v2")
        check("update_record", new_rev == 2)

        try:
            update_record(research_id, 1, {"coverage": "冲突"})
            check("revision conflict 被拒绝", False)
        except RevisionConflict:
            check("revision conflict 被拒绝", True)

        try:
            create_record("insights", {"attribution": "assistant", "user_stance": "maybe"})
            check("非法 user_stance 被拒绝", False)
        except ValueError:
            check("非法 user_stance 被拒绝", True)

        found = find_records("自检", "topics")
        check("find_records", any(f["id"] == topic_id for f in found))

        try:
            create_record(
                "insights",
                {
                    "question": "自检坏认识",
                    "explanation": "临时",
                    "attribution": "assistant",
                    "user_stance": "accepted",
                    "evidence_refs": [],
                    "boundaries": "临时",
                    "open_questions": [],
                    "history": [],
                },
            )
            check("默认 accepted 缺 user_quote 被拒绝", False)
        except ValueError:
            check("默认 accepted 缺 user_quote 被拒绝", True)

        try:
            create_record(
                "research",
                {"question": "自检坏引用", "topic_ids": ["does-not-exist"], "sources": [], "claims": [], "disagreements": [], "unknowns": [], "coverage": ""},
            )
            check("引用不存在记录被拒绝", False)
        except ValueError:
            check("引用不存在记录被拒绝", True)

        try:
            create_record(
                "insights",
                {"attribution": "assistant", "user_stance": "unexpressed", "evidence_refs": [{"record_id": research_id, "source_id": "s1", "relation": "backsup"}]},
            )
            check("非法 evidence relation 被拒绝", False)
        except ValueError:
            check("非法 evidence relation 被拒绝", True)

        try:
            create_record("sessions", {"mode": "research", "status": "running", "next_step": ""})
            check("非法 session status 被拒绝", False)
        except ValueError:
            check("非法 session status 被拒绝", True)

        try:
            create_record(
                "research",
                {"question": "自检坏来源", "sources": [{"source_id": "s1", "access_status": "broken"}], "claims": [], "disagreements": [], "unknowns": [], "coverage": ""},
            )
            check("非法 access_status 被拒绝", False)
        except ValueError:
            check("非法 access_status 被拒绝", True)

        quoted_insight = create_record(
            "insights",
            {
                "question": "自检表态认识",
                "explanation": "临时",
                "attribution": "assistant",
                "user_stance": "partial",
                "evidence_refs": [{"record_id": research_id, "source_id": "s1", "relation": "supports"}],
                "boundaries": "临时",
                "open_questions": [],
                "history": [{"at": "2026-09-11T00:00:00+00:00", "change": "首次", "reason": "自检", "user_quote": "部分认可"}],
            },
        )
        created.append(quoted_insight)
        check("带 user_quote 的 partial 被接受", quoted_insight)

        report = validate_workspace()
        self_issues = [i for i in report["issues"] if any(f"/{rid}]" in i for rid in created)]
        check("自检产生的记录无校验问题", not self_issues)
    finally:
        for record_id in created:
            _, p = _record_path(record_id)
            if p and os.path.exists(p):
                os.remove(p)
        print("  (已清理临时记录)")

    if failures:
        print(f"selftest 失败: {failures}")
        return 1
    print("selftest 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
