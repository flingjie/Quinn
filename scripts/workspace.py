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
    python3 scripts/workspace.py find <query> [kind] [--since YYYY-MM-DD] [--until YYYY-MM-DD]
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
from datetime import datetime, timedelta, timezone

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

KINDS = ("topics", "research", "discussions", "insights", "sessions", "goals", "training_sessions", "attempts", "feedback")
SCHEMA_VERSION = "1"

ATTRIBUTIONS = {"source_author", "assistant", "user"}
USER_STANCES = {"accepted", "partial", "withheld", "rejected", "unexpressed"}
EVIDENCE_RELATIONS = {"supports", "contradicts", "limits", "inconclusive"}
OPEN_QUESTION_STATUSES = {"exploring", "waiting", "settled"}
SESSION_STATUSES = {
    "exploring",
    "paused",
    "closed",
    "active",
    "completed",
    "save_failed",
}
CHANGE_STATUSES = {
    "expressed",
    "original_confirmed",
    "no_change",
    "unconfirmed",
}
ACCESS_STATUSES = {"ok", "partial", "failed"}

GOAL_STATUSES = {"draft", "active", "completed", "archived"}
TRAINING_STATUSES = {
    "draft",
    "active",
    "awaiting_attempt",
    "awaiting_application",
    "reviewed",
    "paused",
    "cancelled",
}
DELIVERY_MODES = {"learning", "demo", "assistance"}
ASSISTANCE_LEVELS = {"independent", "hinted", "template", "demonstrated", "coauthored"}
ASSISTANCE_DETAIL_TYPES = {"hint", "template", "demonstration", "prompt"}
EVIDENCE_KINDS = {"understanding", "application", "transfer"}
FEEDBACK_VERDICTS = {"demonstrated", "needs_work", "insufficient_evidence"}

# 训练闭环状态机白名单（update_record 强制）
TRAINING_TRANSITIONS = {
    "draft": {"active", "cancelled"},
    "active": {"awaiting_attempt", "awaiting_application", "paused", "cancelled"},
    "awaiting_attempt": {"active", "awaiting_application", "reviewed", "paused", "cancelled"},
    "awaiting_application": {"awaiting_attempt", "reviewed", "paused", "cancelled"},
    "paused": {"active", "awaiting_attempt", "awaiting_application", "cancelled"},
    "reviewed": set(),
    "cancelled": set(),
}
GOAL_TRANSITIONS = {
    "draft": {"active", "archived"},
    "active": {"completed", "archived"},
    "completed": set(),
    "archived": set(),
}

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
    for field in ("goal_id", "session_id", "attempt_id"):
        v = fm.get(field)
        if isinstance(v, str) and v:
            refs.add(v)
    for ref in _evidence_refs(fm):
        if ref.get("record_id"):
            refs.add(ref["record_id"])
    return refs


def _check_references(fm: dict) -> None:
    """写约束：不得引用尚不存在的记录（引用记录先落盘，再写引用方）。"""
    for ref in sorted(_referenced_ids(fm)):
        if not _record_path(ref)[0]:
            raise ValueError(f"引用不存在的记录 {ref!r}（先落盘该记录，再引用）")


def _check_kind_ref(fm: dict, field: str, expected_kind: str, issues: list[str], kind: str, record_id: str, ids: dict[str, str]) -> None:
    """校验标量引用指向正确 kind（validate_workspace 用）。"""
    rid = fm.get(field)
    if not rid:
        return
    if rid not in ids:
        issues.append(f"[{kind}/{record_id}] {field} 引用不存在的记录 {rid}")
    elif ids[rid] != expected_kind:
        issues.append(f"[{kind}/{record_id}] {field} 指向非 {expected_kind} 记录 {rid}（实际 {ids[rid]}）")


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
        change_status = fm.get("change_status")
        if change_status is not None and change_status not in CHANGE_STATUSES:
            issues.append(
                f"非法 change_status: {change_status!r}（可选 {sorted(CHANGE_STATUSES)}）"
            )
        for key in ("period_start", "period_end"):
            val = fm.get(key)
            if val is not None and not _is_iso_date(str(val).strip()):
                issues.append(f"非法 {key}: {val!r}（应为 YYYY-MM-DD）")
    elif kind == "goals":
        status = fm.get("status")
        if status is not None and status not in GOAL_STATUSES:
            issues.append(f"非法 status: {status!r}（可选 {sorted(GOAL_STATUSES)}）")
        if not fm.get("desired_behavior"):
            issues.append("缺 desired_behavior（可观察行为目标必填）")
    elif kind == "training_sessions":
        status = fm.get("status")
        if status is not None and status not in TRAINING_STATUSES:
            issues.append(f"非法 status: {status!r}（可选 {sorted(TRAINING_STATUSES)}）")
        dm = fm.get("delivery_mode")
        if dm is not None and dm not in DELIVERY_MODES:
            issues.append(f"非法 delivery_mode: {dm!r}（可选 {sorted(DELIVERY_MODES)}）")
        if not fm.get("goal_id"):
            issues.append("缺 goal_id（训练会话必填目标）")
    elif kind == "attempts":
        al = fm.get("assistance_level")
        if al is not None and al not in ASSISTANCE_LEVELS:
            issues.append(f"非法 assistance_level: {al!r}（可选 {sorted(ASSISTANCE_LEVELS)}）")
        ek = fm.get("evidence_kind")
        if ek is not None and ek not in EVIDENCE_KINDS:
            issues.append(f"非法 evidence_kind: {ek!r}（可选 {sorted(EVIDENCE_KINDS)}）")
        if not fm.get("session_id"):
            issues.append("缺 session_id（尝试必填所属训练会话）")
        for d in fm.get("assistance_details") or []:
            if isinstance(d, dict) and d.get("type") not in ASSISTANCE_DETAIL_TYPES:
                issues.append(f"非法 assistance_details.type: {d.get('type')!r}（可选 {sorted(ASSISTANCE_DETAIL_TYPES)}）")
    elif kind == "feedback":
        if not fm.get("attempt_id"):
            issues.append("缺 attempt_id（反馈必填所属尝试）")
        if not fm.get("rubric_version"):
            issues.append("缺 rubric_version（反馈必填 rubric 版本）")
        for cr in fm.get("criterion_results") or []:
            if isinstance(cr, dict):
                v = cr.get("verdict")
                if v is not None and v not in FEEDBACK_VERDICTS:
                    issues.append(f"非法 criterion_results.verdict: {v!r}（可选 {sorted(FEEDBACK_VERDICTS)}）")
                if v in ("demonstrated", "needs_work") and not cr.get("source_quote"):
                    issues.append(f"verdict={v} 需 source_quote 非空（引用用户尝试原文）")
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


def _check_entry_state(kind: str, fm: dict) -> None:
    """创建时入口态：训练会话与目标须从 draft 起步。"""
    if kind in ("training_sessions", "goals"):
        status = fm.get("status")
        if status != "draft":
            raise ValueError(f"{kind} 创建时 status 须为 'draft'（当前 {status!r}）")


def _check_transition(kind: str, old_fm: dict, new_fm: dict) -> None:
    """校验状态机转换（training_sessions / goals）。状态无变化则不检查。"""
    if kind not in ("training_sessions", "goals"):
        return
    transitions = TRAINING_TRANSITIONS if kind == "training_sessions" else GOAL_TRANSITIONS
    old_status = old_fm.get("status")
    new_status = new_fm.get("status")
    if new_status is None or new_status == old_status:
        return
    allowed = transitions.get(old_status, set())
    if new_status not in allowed:
        raise ValueError(f"非法状态转换: {old_status!r} -> {new_status!r}（允许 {sorted(allowed)}）")


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
    _check_entry_state(kind, fm)
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
        if cur["kind"] == "attempts":
            raise ValueError("attempts 记录不可更新（用户产物不可被覆盖）；修改请新建 attempt")
        fm = dict(cur["frontmatter"])
        new_body = body if body is not None else cur["body"]
        fm.update(payload)
        fm["revision"] = cur["revision"] + 1
        fm["updated_at"] = _now()
        _check_transition(cur["kind"], cur["frontmatter"], fm)
        _validate_frontmatter(fm, cur["kind"])
        _check_references(fm)
        _atomic_write(cur["path"], _serialize(fm, new_body))
    return fm["revision"]


def _is_iso_date(v: str) -> bool:
    """v 是否为合法 YYYY-MM-DD。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return False
    try:
        datetime.strptime(v, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _date_part(value: str | None) -> str | None:
    """把日期参数规范为 YYYY-MM-DD；无效则 ValueError。"""
    if value is None:
        return None
    v = str(value).strip()
    if not v:
        return None
    v = v[:10]
    if not _is_iso_date(v):
        raise ValueError(f"日期参数无效: {value!r}（应为 YYYY-MM-DD 或 ISO 日期）")
    return v


def find_records(
    query: str,
    kind: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict]:
    """元数据及正文全文查找候选，返回 [{id, kind, title, path, updated_at}]。

    `since`/`until` 为可选日期过滤（`YYYY-MM-DD` 或 ISO），按 `updated_at` 的日期
    部分（前 10 位）是否落在闭区间内筛选；缺日期字段的记录在启用过滤时被跳过。
    """
    if kind is not None and kind not in KINDS:
        raise ValueError(f"未知记录类型: {kind!r}（可选 {KINDS}）")
    kinds = [kind] if kind else list(KINDS)
    q = (query or "").strip().lower()
    since_d = _date_part(since)
    until_d = _date_part(until)
    if since_d and until_d and since_d > until_d:
        raise ValueError(f"日期区间无效: since={since_d} 晚于 until={until_d}")
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
            updated_at = ""
            if isinstance(fm, dict):
                title = fm.get("title") or fm.get("topic") or fm.get("question") or fm.get("desired_behavior") or ""
                updated_at = fm.get("updated_at") or ""
            if since_d or until_d:
                day = str(updated_at)[:10]
                if not day:
                    continue
                if since_d and day < since_d:
                    continue
                if until_d and day > until_d:
                    continue
            results.append(
                {
                    "id": name[:-3],
                    "kind": k,
                    "title": title,
                    "path": p,
                    "updated_at": updated_at,
                }
            )
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
        if kind == "training_sessions":
            _check_kind_ref(fm, "goal_id", "goals", issues, kind, record_id, ids)
            _check_kind_ref(fm, "session_id", "sessions", issues, kind, record_id, ids)
        elif kind == "attempts":
            _check_kind_ref(fm, "session_id", "training_sessions", issues, kind, record_id, ids)
        elif kind == "feedback":
            _check_kind_ref(fm, "attempt_id", "attempts", issues, kind, record_id, ids)
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
    p.add_argument("--since", help="只返回 updated_at 日期 >= 此值（YYYY-MM-DD 或 ISO）")
    p.add_argument("--until", help="只返回 updated_at 日期 <= 此值（YYYY-MM-DD 或 ISO）")

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
            _print_json(find_records(args.query, args.kind, args.since, args.until))
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
            "sessions",
            {
                "mode": "explore",
                "topic": "自检探索",
                "topic_ids": [topic_id],
                "record_ids": [research_id],
                "research_ids": [research_id],
                "status": "exploring",
                "change_status": "unconfirmed",
                "next_step": "自检",
            },
        )
        created.append(session_id)
        check("create sessions", session_id)

        legacy_session = create_record(
            "sessions",
            {"mode": "research", "topic_ids": [], "record_ids": [], "status": "completed", "next_step": "旧状态兼容"},
        )
        created.append(legacy_session)
        check("create sessions 旧 status=completed", legacy_session)

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

        found_sessions = find_records("自检探索", "sessions")
        hit = next((f for f in found_sessions if f["id"] == session_id), None)
        check("find_records 含 updated_at 与 topic", bool(hit and hit.get("updated_at") and hit.get("title") == "自检探索"))

        sess_day = read_record(session_id)["frontmatter"]["updated_at"][:10]
        prev_day = (datetime.fromisoformat(sess_day) - timedelta(days=1)).date().isoformat()
        found_since = find_records("自检探索", "sessions", since=sess_day)
        check("find 日期过滤 since=记录日期 包含", any(f["id"] == session_id for f in found_since))
        found_until = find_records("自检探索", "sessions", until=prev_day)
        check("find 日期过滤 until=前一天 排除", not any(f["id"] == session_id for f in found_until))
        try:
            find_records("自检探索", "sessions", since="2026-9-24")
            check("find 非零填充日期被拒绝", False)
        except ValueError:
            check("find 非零填充日期被拒绝", True)
        try:
            find_records("自检探索", "sessions", since="2026-09-30", until="2026-09-01")
            check("find 无效日期区间被拒绝", False)
        except ValueError:
            check("find 无效日期区间被拒绝", True)
        try:
            create_record("sessions", {"mode": "synthesize", "period_start": "2026/07/01"})
            check("非法 period_start 被拒绝", False)
        except ValueError:
            check("非法 period_start 被拒绝", True)

        try:
            create_record("sessions", {"mode": "explore", "status": "exploring", "change_status": "maybe"})
            check("非法 change_status 被拒绝", False)
        except ValueError:
            check("非法 change_status 被拒绝", True)

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

        # --- 训练闭环（P1） ---
        goal_id = create_record(
            "goals",
            {"desired_behavior": "在汇报开头一句话说清问题与需要的决定", "context": "自检", "constraints": [], "evidence_criteria": ["se-goal"], "status": "draft", "record_ids": []},
        )
        created.append(goal_id)
        check("create goals", goal_id)

        ts_id = create_record(
            "training_sessions",
            {"goal_id": goal_id, "delivery_mode": "learning", "task_ref": "structured-expression", "rubric_version": "v1", "status": "draft", "next_step": "自检"},
        )
        created.append(ts_id)
        check("create training_sessions (draft)", ts_id)

        try:
            create_record("training_sessions", {"goal_id": goal_id, "delivery_mode": "learning", "task_ref": "structured-expression", "rubric_version": "v1", "status": "active"})
            check("training_sessions 非 draft 入口被拒", False)
        except ValueError:
            check("training_sessions 非 draft 入口被拒", True)

        try:
            update_record(ts_id, 1, {"status": "reviewed"})
            check("非法转换 draft->reviewed 被拒", False)
        except ValueError:
            check("非法转换 draft->reviewed 被拒", True)

        rev = update_record(ts_id, 1, {"status": "active"})
        check("合法转换 draft->active", rev == 2)
        rev = update_record(ts_id, rev, {"status": "awaiting_attempt"})
        check("合法转换 active->awaiting_attempt", rev == 3)

        attempt_id = create_record(
            "attempts",
            {"session_id": ts_id, "assistance_level": "independent", "evidence_kind": "understanding", "assistance_details": []},
            "用户尝试原文（自检）",
        )
        created.append(attempt_id)
        check("create attempts (independent)", attempt_id)

        try:
            update_record(attempt_id, 1, {"assistance_level": "hinted"})
            check("attempt 不可变被拒", False)
        except ValueError:
            check("attempt 不可变被拒", True)

        try:
            create_record("attempts", {"session_id": ts_id, "assistance_level": "fully_independent", "evidence_kind": "understanding"})
            check("非法 assistance_level 被拒", False)
        except ValueError:
            check("非法 assistance_level 被拒", True)

        try:
            create_record("feedback", {"rubric_version": "v1", "criterion_results": [], "next_action": ""})
            check("feedback 缺 attempt_id 被拒", False)
        except ValueError:
            check("feedback 缺 attempt_id 被拒", True)

        try:
            create_record("feedback", {"attempt_id": "no-such-attempt", "rubric_version": "v1", "criterion_results": [], "next_action": ""})
            check("feedback 引用不存在 attempt 被拒", False)
        except ValueError:
            check("feedback 引用不存在 attempt 被拒", True)

        try:
            create_record(
                "feedback",
                {"attempt_id": attempt_id, "rubric_version": "v1", "criterion_results": [{"criterion_id": "se-goal", "verdict": "demonstrated"}], "next_action": ""},
            )
            check("verdict=demonstrated 缺 source_quote 被拒", False)
        except ValueError:
            check("verdict=demonstrated 缺 source_quote 被拒", True)

        feedback_id = create_record(
            "feedback",
            {
                "attempt_id": attempt_id,
                "rubric_version": "v1",
                "evidence_spans": [{"quote": "用户尝试原文", "criterion_id": "se-goal"}],
                "criterion_results": [{"criterion_id": "se-goal", "verdict": "needs_work", "source_quote": "用户尝试原文", "missing_info": "未说明依据", "improvement_action": "把第一句改为现状+需要决定"}],
                "next_action": "把第一句改为「现状是 X，需要你们决定 Y」",
                "user_corrections": [],
            },
        )
        created.append(feedback_id)
        check("create feedback", feedback_id)

        frev = update_record(feedback_id, 1, {"user_corrections": [{"at": "2026-10-22T00:00:00+00:00", "correction": "用户纠正", "note": "自检"}]})
        frec = read_record(feedback_id)
        check("feedback 追加 user_corrections 递增 revision", frev == 2 and frec["revision"] == 2)
        check("feedback 保留原 criterion_results", frec["frontmatter"]["criterion_results"][0]["verdict"] == "needs_work")

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
