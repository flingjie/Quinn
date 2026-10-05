# Quinn 内外部平衡优化：映射结论

日期：2026-10-05
状态：已落地。本文是对外部设计文档《Quinn 优化实施 Plan：在外部反馈中修正判断，保有自己的方向》的映射结论；原始设计在仓库外，本文只存口径与落点，不替代现行产品契约。

## 口径校准

外部设计把 Quinn 描述为「商业判断训练」并提到评分/等级/排名。现行产品契约（`docs/Quinn-Product-Contract.md`）已把案例训练推迟（§6）、把评分/等级归入历史方案（§7）。经确认，本次按**探索产品**口径落地，不复活评分。

设计的实质——关键时刻问清目标与取舍、用具体证据反馈判断、让行动结果改变下一次判断——与现行探索产品契合，作为增量扩展。

## 映射总表

| 外部设计组件 | 落点 |
| --- | --- |
| §3 关键决策交互 | `skills/quinn-explore/references/mentor-interaction.md`（介入信号、导师四件事、反馈） |
| §4 决策记录 | `skills/quinn-synthesize/references/session-format.md`（body 小节，不加 frontmatter） |
| §5 反馈机制 | `mentor-interaction.md`（任务类型→反馈选择 + 三要素） |
| §6 复盘机制 | `quinn-synthesize/SKILL.md` + `session-format.md`（行动复盘） |
| §7 五个接入点 | 均为逻辑职责：导师交互 Skill、会话策略层、决策领域服务、反馈策略层、复盘领域服务 |
| §9 验证 | `evals/scenarios.md`（24 场景矩阵） |
| §10 回退开关 | `workspace/config.md`（gitignore，操作开关） |

## 关键取舍

- 不复活评分/等级；「训练反馈」落地为「证据反馈」。
- 决策字段全在 session body 小节，不加 frontmatter、不改 `scripts/workspace.py`、不升 `schema_version`。
- 开关用 `workspace/config.md`，与 `workspace/profile.md`（长期偏好）分开。

## 改动文件

- `skills/quinn-explore/references/mentor-interaction.md`
- `skills/quinn-explore/SKILL.md`
- `workspace/config.md`、`workspace/examples/config.md`、`.gitignore`
- `evals/scenarios.md`
- `skills/quinn-synthesize/references/session-format.md`
- `skills/quinn-synthesize/SKILL.md`
- `shared/contracts.md`
