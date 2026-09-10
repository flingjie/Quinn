# 训练记录目录（sessions）

本目录由 Skill 在训练过程中写入，每条训练一份 JSON 文件，文件名为 `session_YYYYMMDD_NNN.json`（`NNN` 为当日序号，从 `001` 递增）。

## 最小结构

```json
{
  "id": "session_20260910_001",
  "case_id": "case_001",
  "case_revision": "v1",
  "started_at": "2026-09-10T10:00:00Z",
  "completed_at": null,
  "stage": "awaiting_initial",
  "mode": "practice",
  "prompt_level": "basic",
  "initial_raw": null,
  "challenge": null,
  "updated_raw": null,
  "feedback": null,
  "transfer_from_session_id": null,
  "outcome_revealed": false,
  "rubric_version": "v1"
}
```

## 字段说明

- `stage`：`awaiting_initial`（已出题、待初判）/ `awaiting_update`（已挑战、待更新）/ `completed`（已完成）。
- `mode`：`practice`（基础练习）/ `transfer`（变式复测）。
- `prompt_level`：`basic`（无提示）/ `open`（复测默认）/ `assisted`（训练期间获得额外提示）。
- `challenge`：非空时含 `text`、`target_assumption`、`reason`。
- `feedback`：含 `primary_dimension`、`initial_score`、`updated_score`、`evidence`、`update_assessment`、`next_focus`；分数允许 `null`。
- `transfer_from_session_id`：变式题指向原训练 session id。
- `initial_raw` / `updated_raw`：保存用户原文，不被润色版覆盖。

## 规则

- 原文优先：纠错或补充单独追加，不覆盖原文。
- 同一训练重复保存更新同一文件，不新增重复记录。
- 复盘只读 `stage = completed` 的记录；未完成训练不计作学习表现。
