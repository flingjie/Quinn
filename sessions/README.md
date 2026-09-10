# 训练记录目录（sessions）

本目录由 Skill 在训练过程中写入，每题一份 JSON，文件名为 `session_YYYYMMDD_NNN.json`（`NNN` 为当日序号，从 `001` 递增）。保存无法重建的原始证据。

## 最小结构

```json
{
  "schema_version": 1,
  "id": "session_20260910_001",
  "case_id": "case_005",
  "case_revision": "v1",
  "started_at": "2026-09-10T10:00:00Z",
  "completed_at": null,
  "stage": "awaiting_initial",
  "mode": "practice",
  "transfer_from_session_id": null,
  "initial_help": "none",
  "turns": [],
  "feedback": null
}
```

## 字段说明

- `stage`：`awaiting_initial`（已出题、待初判）/ `awaiting_response`（已挑战、待后续回答）/ `completed`（已完成）。
- `mode`：`practice`（基础）/ `transfer`（变式复测）/ `repeat`（重练）。
- `transfer_from_session_id`：变式题指向原训练 session id。
- `initial_help`：`none` / `provided` / `unknown`，表示初判前有无教学帮助；正常基础提问不算教学帮助。复测受提示标 `provided`，后续不能反向修改初判时的状态。
- `turns`：按发生顺序保存 `role`（user/coach）、`kind`、`text`。`kind` 可为 `initial`（初判）、`challenge`（挑战）、`help`（明确教学帮助）、`response`（后续回答）、`clarification`（澄清）。**第一条 `initial` 即冻结的初判，后续补充追加、不能覆盖。**
- `feedback`：含 `initial_score`、`assisted_score`、`evidence`、`next_focus`；每条 `evidence` 引用具体 turn 序号及原文；复测附 `transfer_note` 说明是否主动识别目标关系及证据限制。

## 保存要求

- 收到用户内容后先保存原文，再生成后续分析。
- 挑战保存成功后再展示；同一 Session 重试更新同一文件，不新增重复记录。
- 保存失败说明情况，保留当前内容用于重试，不声称成功。
- 初期直接写 JSON，保存后检查 JSON 可读、原文与关键字段完整。
- 发生真实保存摩擦后，再补原子写入与结构校验的小脚本。

## 兼容

`schema_version` 只描述本版结构。旧格式（v2 分离字段）只读兼容，不批量改写；无法恢复旧提示状态时标 `unknown`，不能计为无提示证据；旧评分不按新规则追溯覆盖。
