# 任务配方与 rubric 注册表

Rubric 是仓库内的版本化 spec 文件（非 workspace 记录）。记录只 pin `rubric_version` 字符串；git 历史保留每个版本正文。改 rubric 时新增版本节并把 `current_version` 前移，旧记录仍引用旧版本。

| task_ref | 文件 | current_version |
| --- | --- | --- |
| `structured-expression` | `structured-expression.md` | `v1` |
| `judgment-verification` | `judgment-verification.md` | `v1` |

每份 rubric 含：task_type id、版本、2–4 个带稳定 `criterion_id` 的可观察标准、可观察定义、正/反例、该标准下 `needs_work` vs `insufficient_evidence` 的含义。

后续能力复用既有定义，不另建循环：`skills/quinn-brainstorming/references/question-patterns.md`（八能力）、`skills/quinn-explore/references/transfer-practice.md`（迁移）、`skills/quinn-explore/references/mentor-interaction.md`（判断反馈三点）。
