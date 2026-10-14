# Quinn 融会贯通与举一反三（迁移练习）优化：映射结论

日期：2026-10-14
状态：待实施（P0 已核查）。本文是对外部设计文档《Quinn-Transfer-Thinking-Optimization-Plan.md》的映射结论；原始设计在仓库外，本文只存口径与落点，不替代现行产品契约。

## 口径校准

外部设计把 Quinn 描述为「帮用户练习三种能力：提炼共同机制、迁移到新问题、识别迁移成立条件与失效边界」。现行产品契约（`docs/Quinn-Product-Contract.md`）已把案例训练推迟（§6，用户主动要求时的一种可选练习）、把评分/等级归入历史方案（§7）。经确认，本次按**可选练习**口径落地，不复活评分与能力等级。

设计核心——示范 → 用户尝试 → 具体反馈 → 条件变化 → 后续重用——是「迁移动作」（explore 步骤 7 的一次性邀请）的深化，作为**用户明确发起、可随时退出**的增量扩展；记录只用描述态（未作答 / 跳过 / 已示范（复述）/ 有提示后完成 / 本次无提示完成），示范后复述 ≠ 独立迁移、提示后正确须保留提示上下文、机制名先给出只记「已知机制应用」。

## 映射总表

| 外部设计组件 | 落点 |
| --- | --- |
| §3 启动与模式选择（路由规则、三种方式） | `skills/quinn-explore/SKILL.md`「练习模式」路由表 |
| §4 一次迁移练习的最小协议 | `skills/quinn-explore/references/transfer-practice.md`（新建，核心） |
| §5 迁移质量合同 | `transfer-practice.md`（内部五查 + 比喻/迁移假设/实际证据三分） |
| §6 完整交互示例 | `transfer-practice.md`（最小协议与归属规则落地为可执行步骤） |
| §7 记录与后续重用 | `skills/quinn-synthesize/references/session-format.md`「迁移练习」正文小节 + `skills/quinn-synthesize/SKILL.md`「迁移练习的保存与重用」 |
| §8 结构化与可视化接入 | 复用 Markdown 表格与必要 Mermaid，不建独立画布/交互网页 |
| §10 验收场景与验证方法 | `evals/scenarios.md`（迁移练习场景矩阵 v7 + 试用记录） |

## 关键取舍

- 不复活评分/等级；「练习反馈」落地为「按实际推导的具体反馈」，只用描述态。
- 记录全在 session 正文小节，不加 frontmatter、不改 `scripts/workspace.py`、不升 `schema_version`（对齐 `d84c4ba` 的 body-only 落法）。
- 不新增 `workspace/config.md` 开关：练习路径本就是 opt-in（只有用户明确要求才进入），没有默认开启的行为可关；若用户想关掉自然结束处的单次迁移邀请，正确落点是 `workspace/profile.md`（长期偏好），非操作开关。
- explore 步骤 7 的单次迁移邀请仍是唯一半自动触点，不升级成多轮练习循环。

## 改动文件

- `skills/quinn-explore/references/transfer-practice.md`（新建）
- `skills/quinn-explore/SKILL.md`
- `skills/quinn-synthesize/references/session-format.md`
- `skills/quinn-synthesize/SKILL.md`
- `evals/scenarios.md`
- `README.md`
- `AGENTS.md`

不改：`shared/contracts.md`、`scripts/workspace.py`、`workspace/config.md`、`skills/quinn-research/*`（已区分事实/类比/假设并规定跨域证据边界，无需改动）。
