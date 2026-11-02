# workspace.py 内部重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `scripts/workspace.py` 的校验改为声明式规则表、selftest 拆到独立文件、`validate_workspace` 去掉重复解析——对外行为零变化。

**Architecture:** 三步独立重构：(1) `_collect_issues` 的 if/elif 链改为 `KIND_RULES` 规则表 + 跨字段特例函数；(2) `validate_workspace` 第二遍复用第一遍解析的 frontmatter；(3) `_selftest` 整体搬到 `scripts/workspace_selftest.py`，CLI 委托调用。每步用现有 selftest + validate 基线 diff 验证。

**Tech Stack:** Python 3 标准库 + PyYAML（不新增依赖）。无 pytest，测试载体是脚本自带 selftest。

**Spec:** `docs/superpowers/specs/2026-11-02-workspace-refactor-design.md`

## Global Constraints

- 对外行为零变化：CLI 命令、公开函数签名、校验规则、错误信息文案逐字一致。
- 错误信息格式：枚举类 `非法 {field}: {value!r}（可选 {sorted(enum)}）`；必填类 `缺 {field}（{说明}）`——与现有文案逐字相同。
- selftest 用例一条不删、一条不改（搬移时函数体逐字保留）。
- 不改枚举值、状态机白名单、入口态规则；不动 `notion.py` 与任何文档。
- 工作目录：`/Users/lingjiefan/underway/Quinn`。

---

### Task 1: 记录重构前基线

**Files:**
- 不改代码；产出 `/tmp/quinn_validate_baseline.json`

**Interfaces:**
- Produces: 基线文件 `/tmp/quinn_validate_baseline.json`，后续所有 Task 用它做 diff。

- [ ] **Step 1: 跑 selftest 确认当前全部通过**

Run: `python3 scripts/workspace.py selftest`
Expected: 末行 `selftest 通过`，退出码 0。若失败，停止并报告——基线本身有问题时不能开始重构。

- [ ] **Step 2: 保存 validate 基线**

Run: `python3 scripts/workspace.py validate > /tmp/quinn_validate_baseline.json && cat /tmp/quinn_validate_baseline.json`
Expected: JSON 输出含 `issues` 与 `summary`（当前真实 workspace 约 22 条记录）。

---

### Task 2: `_collect_issues` 改为声明式 KIND_RULES

**Files:**
- Modify: `scripts/workspace.py`（替换 `_collect_issues` 函数，位于「基础工具」段，约 259–337 行；在其上方新增 `KIND_RULES`、`KIND_CHECKS` 与四个特例函数）

**Interfaces:**
- Consumes: 现有枚举常量 `SESSION_STATUSES`、`CHANGE_STATUSES`、`GOAL_STATUSES`、`TRAINING_STATUSES`、`DELIVERY_MODES`、`ASSISTANCE_LEVELS`、`ASSISTANCE_DETAIL_TYPES`、`EVIDENCE_KINDS`、`FEEDBACK_VERDICTS`、`ATTRIBUTIONS`、`USER_STANCES`、`OPEN_QUESTION_STATUSES`、`ACCESS_STATUSES`、`EVIDENCE_RELATIONS`，助手 `_is_iso_date`、`_evidence_refs`。
- Produces: `_collect_issues(fm: dict, kind: str) -> list[str]` 签名与返回值不变；新增模块级 `KIND_RULES: dict`、`KIND_CHECKS: dict` 供后续维护（本计划内无其他 Task 依赖）。

- [ ] **Step 1: 用下列代码替换原 `_collect_issues` 函数**

删除现有 `def _collect_issues(...)` 整个函数（从 `def _collect_issues` 到 `return issues`），在原位置写入：

```python
# 每 kind 的声明式校验规则：enums = {字段: 合法枚举}，required = ((字段, 缺失说明), ...)
KIND_RULES = {
    "sessions": {
        "enums": {"status": SESSION_STATUSES, "change_status": CHANGE_STATUSES},
        "required": (),
    },
    "goals": {
        "enums": {"status": GOAL_STATUSES},
        "required": (("desired_behavior", "可观察行为目标必填"),),
    },
    "training_sessions": {
        "enums": {"status": TRAINING_STATUSES, "delivery_mode": DELIVERY_MODES},
        "required": (("goal_id", "训练会话必填目标"),),
    },
    "attempts": {
        "enums": {"assistance_level": ASSISTANCE_LEVELS, "evidence_kind": EVIDENCE_KINDS},
        "required": (("session_id", "尝试必填所属训练会话"),),
    },
    "feedback": {
        "enums": {},
        "required": (("attempt_id", "反馈必填所属尝试"), ("rubric_version", "反馈必填 rubric 版本")),
    },
}


def _check_stance_quote(fm: dict, issues: list[str]) -> None:
    """user_stance 为明确表态时，history 须含 user_quote 原话依据。"""
    stance = fm.get("user_stance")
    if stance in ("accepted", "partial", "withheld", "rejected"):
        history = fm.get("history") or []
        if not any(isinstance(h, dict) and h.get("user_quote") for h in history):
            issues.append(f"user_stance={stance} 但 history 缺少 user_quote（表态需原话依据，防默认接受）")


def _check_session_dates(fm: dict, issues: list[str]) -> None:
    """sessions 可选的 period_start / period_end 须为 YYYY-MM-DD。"""
    for key in ("period_start", "period_end"):
        val = fm.get(key)
        if val is not None and not _is_iso_date(str(val).strip()):
            issues.append(f"非法 {key}: {val!r}（应为 YYYY-MM-DD）")


def _check_assistance_details(fm: dict, issues: list[str]) -> None:
    """attempts 的 assistance_details[].type 枚举校验。"""
    for d in fm.get("assistance_details") or []:
        if isinstance(d, dict) and d.get("type") not in ASSISTANCE_DETAIL_TYPES:
            issues.append(f"非法 assistance_details.type: {d.get('type')!r}（可选 {sorted(ASSISTANCE_DETAIL_TYPES)}）")


def _check_criterion_results(fm: dict, issues: list[str]) -> None:
    """feedback 的 criterion_results[].verdict 枚举与 source_quote 联动。"""
    for cr in fm.get("criterion_results") or []:
        if isinstance(cr, dict):
            v = cr.get("verdict")
            if v is not None and v not in FEEDBACK_VERDICTS:
                issues.append(f"非法 criterion_results.verdict: {v!r}（可选 {sorted(FEEDBACK_VERDICTS)}）")
            if v in ("demonstrated", "needs_work") and not cr.get("source_quote"):
                issues.append(f"verdict={v} 需 source_quote 非空（引用用户尝试原文）")


# 规则表之外的跨字段特例检查（按 kind 调用，顺序与原 if/elif 链一致）
KIND_CHECKS = {
    "sessions": (_check_session_dates,),
    "attempts": (_check_assistance_details,),
    "feedback": (_check_criterion_results,),
}


def _collect_issues(fm: dict, kind: str) -> list[str]:
    """对单个 frontmatter 做枚举与归属校验，返回问题列表（无记录前缀）。"""
    issues: list[str] = []
    attr = fm.get("attribution")
    if attr is not None and attr not in ATTRIBUTIONS:
        issues.append(f"非法 attribution: {attr!r}（可选 {sorted(ATTRIBUTIONS)}）")
    stance = fm.get("user_stance")
    if stance is not None and stance not in USER_STANCES:
        issues.append(f"非法 user_stance: {stance!r}（可选 {sorted(USER_STANCES)}）")
    _check_stance_quote(fm, issues)
    rules = KIND_RULES.get(kind)
    if rules:
        for field, allowed in rules["enums"].items():
            v = fm.get(field)
            if v is not None and v not in allowed:
                issues.append(f"非法 {field}: {v!r}（可选 {sorted(allowed)}）")
        for field, note in rules["required"]:
            if not fm.get(field):
                issues.append(f"缺 {field}（{note}）")
    for check in KIND_CHECKS.get(kind, ()):
        check(fm, issues)
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
```

注意顺序约束（保证 issues 列表顺序与重构前逐条一致）：通用项（attribution → user_stance → stance quote）→ 规则表 enums（按字典插入顺序）→ 规则表 required → KIND_CHECKS → 通用嵌套项（open_questions → sources → evidence relation）。

- [ ] **Step 2: 跑 selftest 验证全部通过**

Run: `python3 scripts/workspace.py selftest`
Expected: `selftest 通过`，退出码 0。selftest 覆盖了非法 user_stance / change_status / session status / access_status / evidence relation / assistance_level、缺 attempt_id、缺 source_quote、非 draft 入口等错误路径，文案不一致会直接失败。

- [ ] **Step 3: validate 输出与基线 diff**

Run: `python3 scripts/workspace.py validate > /tmp/quinn_validate_after_t2.json && diff /tmp/quinn_validate_baseline.json /tmp/quinn_validate_after_t2.json`
Expected: 无输出（完全一致），退出码 0。

- [ ] **Step 4: 错误文案抽查（规则表路径）**

Run:
```bash
echo '{"status": "draft"}' | python3 scripts/workspace.py create goals -
```
Expected: stderr 输出 `错误: 缺 desired_behavior（可观察行为目标必填）`，退出码 1。

- [ ] **Step 5: Commit**

```bash
git add scripts/workspace.py
git commit -m "refactor: _collect_issues 改为 KIND_RULES 声明式规则表 + 跨字段特例函数（行为不变）"
```

---

### Task 3: `validate_workspace` 复用第一遍解析结果

**Files:**
- Modify: `scripts/workspace.py`（`validate_workspace` 函数，约 572–636 行）

**Interfaces:**
- Consumes: `_collect_issues`（Task 2 重构后签名不变）、`_parse_file`、`_evidence_refs`、`_check_kind_ref`、`_kind_dir`。
- Produces: `validate_workspace() -> dict` 签名与输出结构不变。

- [ ] **Step 1: 用下列代码替换 `validate_workspace` 函数**

```python
def validate_workspace() -> dict:
    """检查结构、引用完整性与归属约束，返回 {issues, summary}。"""
    issues: list[str] = []
    ids: dict[str, str] = {}
    fms: dict[str, dict] = {}
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
            # 重复 ID 时保留首个（KINDS 顺序），与原先 _record_path 的选取一致
            fms.setdefault(record_id, fm)
            if fm.get("id") != record_id:
                issues.append(f"[{kind}/{record_id}] id 与文件名不一致")
            for field in RESERVED_FIELDS:
                if field not in fm:
                    issues.append(f"[{kind}/{record_id}] 缺少公共字段 {field}")
            if not isinstance(fm.get("revision"), int) or fm.get("revision", 0) < 1:
                issues.append(f"[{kind}/{record_id}] revision 非法")
            for msg in _collect_issues(fm, kind):
                issues.append(f"[{kind}/{record_id}] {msg}")
    # 引用完整性（复用第一遍解析结果，不再重新读文件）
    for record_id, kind in ids.items():
        fm = fms[record_id]
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
```

与原版的唯一差异：第二遍不再 `_record_path` + `open` + `_parse_file`，直接取 `fms[record_id]`。

- [ ] **Step 2: 跑 selftest**

Run: `python3 scripts/workspace.py selftest`
Expected: `selftest 通过`，退出码 0。

- [ ] **Step 3: validate 输出与基线 diff**

Run: `python3 scripts/workspace.py validate > /tmp/quinn_validate_after_t3.json && diff /tmp/quinn_validate_baseline.json /tmp/quinn_validate_after_t3.json`
Expected: 无输出，退出码 0。

- [ ] **Step 4: Commit**

```bash
git add scripts/workspace.py
git commit -m "refactor: validate_workspace 第二遍复用首遍解析结果，去掉重复 open+parse"
```

---

### Task 4: selftest 拆到 `scripts/workspace_selftest.py`

**Files:**
- Create: `scripts/workspace_selftest.py`
- Modify: `scripts/workspace.py`（main 的 selftest 分支，约 713–714 行；删除整个 `_selftest` 函数，约 721–1043 行；顶部 docstring 不变）

**Interfaces:**
- Consumes: `workspace` 模块的 `create_record` / `read_record` / `update_record` / `delete_record` / `find_records` / `validate_workspace` / `RevisionConflict` / `_record_path` / `_kind_dir`（签名均不变）。
- Produces: `workspace_selftest.run() -> int`，被 `workspace.py` 的 `selftest` 子命令委托调用；也可直接 `python3 scripts/workspace_selftest.py` 运行。

- [ ] **Step 1: 创建 `scripts/workspace_selftest.py`**

文件骨架如下；`run()` 的函数体是**原 `_selftest` 函数体逐字搬移**（从 `import shutil` 到 `return 0`，缩进不变，包括原有的 `import shutil` 行，一个字不改）：

```python
#!/usr/bin/env python3
"""workspace.py 自检用例（从 workspace.py 拆出，用例与输出不变）。

用法：
    python3 scripts/workspace_selftest.py
    python3 scripts/workspace.py selftest   # 委托本模块
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workspace import (
    RevisionConflict,
    _kind_dir,
    _record_path,
    create_record,
    delete_record,
    find_records,
    read_record,
    update_record,
    validate_workspace,
)


def run() -> int:
    """临时记录自检，验证后清理。"""
    # <此处为原 workspace.py _selftest 函数体逐字搬移，不改任何用例>
    ...


if __name__ == "__main__":
    sys.exit(run())
```

- [ ] **Step 2: 修改 `workspace.py`：删除 `_selftest`，selftest 分支改为委托**

main 中：

```python
        elif args.cmd == "selftest":
            from workspace_selftest import run as _selftest_run
            return _selftest_run()
```

然后删除整个 `def _selftest() -> int:` 函数（含其上方的分隔注释如有）。文件顶部 docstring 中 `selftest` 用法行保持不变。

- [ ] **Step 3: 两种调用方式分别验证**

Run: `python3 scripts/workspace.py selftest && python3 scripts/workspace_selftest.py`
Expected: 两次均输出全部 `✓` 行与 `selftest 通过`，退出码 0；`✓` 用例条数与 Task 1 Step 1 输出的条数相同（搬移不增减用例）。

- [ ] **Step 4: validate 输出与基线 diff + 行数确认**

Run: `python3 scripts/workspace.py validate > /tmp/quinn_validate_after_t4.json && diff /tmp/quinn_validate_baseline.json /tmp/quinn_validate_after_t4.json && wc -l scripts/workspace.py scripts/workspace_selftest.py`
Expected: diff 无输出；`workspace.py` 约 720 行。

- [ ] **Step 5: Commit**

```bash
git add scripts/workspace.py scripts/workspace_selftest.py
git commit -m "refactor: selftest 拆至 scripts/workspace_selftest.py，CLI 委托调用（用例不变）"
```

---

## 完成标准

- 三个 commit，`python3 scripts/workspace.py selftest`、`python3 scripts/workspace_selftest.py`、`python3 scripts/workspace.py validate` 全部通过且 validate 输出与重构前基线逐字一致。
- `scripts/workspace.py` 收缩到约 720 行，无 `_selftest`。
