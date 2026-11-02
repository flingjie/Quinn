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

        # --- 删除 ---
        del_orphan = create_record(
            "sessions",
            {"mode": "explore", "topic": "自检删除孤儿", "topic_ids": [], "record_ids": [], "research_ids": [], "status": "exploring", "next_step": ""},
        )
        created.append(del_orphan)
        delete_record("sessions", del_orphan)
        check("delete 未被引用记录成功且文件消失", not os.path.exists(os.path.join(_kind_dir("sessions"), del_orphan + ".md")))

        try:
            delete_record("research", research_id)
            check("delete 被引用记录被拒", False)
        except ValueError as e:
            check("delete 被引用记录被拒并列引用者", "引用" in str(e))

        try:
            delete_record("sessions", "no-such-record")
            check("delete 不存在记录报错", False)
        except FileNotFoundError:
            check("delete 不存在记录报错", True)

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
    sys.exit(run())
