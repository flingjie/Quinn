# 会话格式（按需加载）

主记录是 `workspace/sessions/<id>.md`。一次探索维护一份；重复保存更新同一 ID。

## Frontmatter

脚本自动写入：`id`、`schema_version`（当前仍为 `"1"`）、`revision`、`created_at`、`updated_at`。Agent 提供的字段：

| 字段 | 说明 |
| --- | --- |
| `mode` | 当前主 Skill，如 `explore` / `research` / `synthesize` |
| `topic` | 短标题，供恢复检索（可选） |
| `topic_ids` | 关联旧专题（可选，默认可 `[]`） |
| `record_ids` | 关联其他记录（可选） |
| `research_ids` | 本次实际读过的研究记录 ID |
| `status` | `exploring` / `paused` / `closed`；旧值 `active` / `completed` / `save_failed` 仍合法 |
| `change_status` | `expressed` / `original_confirmed` / `no_change` / `unconfirmed` |
| `next_step` | 一句继续位置 |

`status` 仅标记进度，不驱动执行；`closed` 不等于结论正确。

## 正文小节

按需记录，空则省略：

| 小节 | 约束 |
| --- | --- |
| 原问题 | 保留用户原话或标记为转述 |
| 原先理解 | 只记用户已表达内容，未知写「未表达」 |
| 目标与取舍（可选） | desired_outcome：本次想获得的结果，仅记用户说明或明确确认；未说明写「未表达」。stated_constraints：愿守住的约束/取舍，保存用户原意，不推断人格 |
| 原判断与类型（可选） | 保留原文，类型只是可纠正的内部标记 |
| 使用的转换算子（可选） | 只记实际影响讨论的 1–2 个，不记录所有尝试 |
| 候选重构与所需证据（可选） | 区分 Quinn 候选与用户已确认内容 |
| 导师判断与依据（可选） | Quinn 的候选洞察、引用依据、替代解释与信心边界 |
| 建议与代价（可选） | 建议、主要代价及改判条件；未获用户认可时标为 Quinn 候选 |
| 假设与验证动作（可选） | assumptions：每条含 claim、依据、unknowns、revision_condition；Quinn 提出的标「Quinn 候选」，未经认可不得写为用户立场。next_action：description、completion_criteria、effort_limit、review_at；是 Quinn 提议，用户接受后才算承诺 |
| 选中方向与触发材料 | 实际探索过的机制及来源 |
| 用户迁移 | 用户自己的推导，可缺省 |
| 当前理解 | 区分「用户表达」与「Quinn 候选总结」 |
| 用户自述背景（可选） | user_stated_context：仅保存用户主动表达或明确确认的内容；一次回答不成为永久画像；与长期偏好（profile）分开 |
| 开放问题 | 真正未解决的疑点 |
| 后续证据或行动 | 发生后追加，不预填成功 |
| 继续位置 | 一句说明下一次从哪里接上 |
| 纠正与修订（可选） | 用户纠错时追加，保留原历程 |

禁止：把模型总结写成用户立场；为“有变化”而编造前后差异；保存失败却报告成功。

## 回看记录

回看是 synthesize 的按需用法，复用 session 记录（不新增 kind）。frontmatter 映射：

| 字段 | 回看取值 |
| --- | --- |
| `mode` | `synthesize` |
| `topic` | `回看 <起>~<止>：<主题>` |
| `record_ids` | 源会话 ID 列表（引用完整性校验） |
| `period_start` / `period_end` | 可选，`YYYY-MM-DD`，仅回看填写 |
| `status` | `exploring`（draft）/ `paused`（discussed）/ `closed` |
| `change_status` | 通常 `unconfirmed` |

回看正文小节（按需，空则省略）：

| 小节 | 约束 |
| --- | --- |
| 回看范围 | 起止日期 + 参考 N 次讨论，日期为实际覆盖范围 |
| 过去发生了什么 | 2–3 条，每条附会话 `id`/日期 |
| 值得重新检查的判断 | 1–2 条，区分「用户原话」与「Quinn 解读」 |
| 开放问题 | ≤3 条，真正未解决 |
| 下一阶段方向（候选） | 仅当用户要求讨论；确认后标记「用户选择」 |
| 回访条件 | 何种新证据/尝试/时间节点时再看，可为空 |
| 覆盖缺口 | 哪些领域未进入记录 |

「纠正与修订」「继续位置」复用普通 session 小节。观察条数有限；无记录只写覆盖缺口，不编造变化。

## 行动复盘（可选）

当用户复盘一次已采取的行动（「复盘这次行动」「上次那个实验结果怎么样」）时，在回看记录或普通 session 中按需加入以下小节；空则省略：

| 小节 | 约束 |
| --- | --- |
| 行动结果 | 预期 vs 实际：结果是否支持原判断 |
| 假设检验 | 成立 / 未执行 / 已否证；**未执行不得记为已否证** |
| 资源代价 | 投入是否超过用户声明的上限；即使结果好也检查是否可持续 |
| 更新决定 | 维持目标 / 调整假设 / 改变方法 / 重新确认目标（由用户决定，Quinn 给建议） |

单次结果不足时保留不确定性，不强行归因。

## 与旧记录的关系

- `discussions` / `insights` / `topics` 种类仍存在，旧文件可读。
- 默认探索闭环只写 session（+ 按需 research）。
- 不批量给旧文件补新字段。
