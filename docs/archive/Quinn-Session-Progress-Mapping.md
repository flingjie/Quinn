# Quinn 会话进展重构 —— 文档 ↔ 现有实现映射

日期：2026-10-29  
状态：现行。外部设计文档 `quinn-session-progress-implementation-plan.md`（「围绕用户变化组织探索与实践」）落到现有仓库的映射与改动清单。该外部文档自述「尚未检查 Quinn 最新仓库」，本文即完成这项映射。

结论先行：**外部文档要求的绝大部分已实现**，只是命名不同。真正缺口只有一处代码（删除命令）与若干收口/命名对账。范围按用户确认限定 **P0–P2**；P3（小实验）已被 `transfer-practice` / `jitou` / `quinn-practice` 训练闭环覆盖，P4（真实会话验证）留待实际使用。

## 1. 逻辑字段 → 现有实现

| 外部文档逻辑字段 | 现有实现 | 状态 |
| --- | --- | --- |
| `session_id` / `topic_id` | session `id` + `topic_ids`（可空）；问题拆分后允许关联 | 已覆盖 |
| `question_initial` | session 正文「原问题」（保留原话或标转述） | 已覆盖 |
| `question_current` | 正文「当前理解」分列「用户表达 / Quinn 候选总结」 | 已覆盖（已标注是否用户原话） |
| `help_direction`（understand / reflect / practice / unknown） | `mode`（explore/research/synthesize/brainstorming/jitou）+ `mentor-interaction.md` 三态意图（solve/practice/unknown） | **映射，不新增字段**（见 §4） |
| `candidate_explanations` | 正文「候选重构与所需证据」「当前理解（Quinn 候选）」 | 已覆盖（允许相互竞争） |
| `observed_changes` | `change_status` + 正文变化小节 | 已覆盖（用户表达为据） |
| `user_reported_feelings` | 正文「用户反应 / 解释」（`experience-reflection.md`） | 已覆盖（默认可不记） |
| `open_questions` | 正文「开放问题」小节 | 已覆盖 |
| `chosen_next_step` | `next_step` + 正文「后续证据或行动」「建议与代价」 | 已覆盖（确认后才标「用户选择」） |
| `confirmation`（proposed/confirmed/corrected/rejected） | `user_stance` + `change_status` + 经历复盘「用户回应」（confirmed/revised/rejected/unexpressed） | **命名对账**（见 §3） |
| `resume_note` | 正文「继续位置」小节 + `next_step` | 已覆盖 |

`help_direction` 映射关系：understand → `mode: explore`/`research`；reflect → `mode: synthesize`（回看/复盘）；practice → `quinn-practice` 或 explore 内迁移练习；unknown → 未定意图前（`mentor-interaction.md` 三态意图）。不新增 frontmatter 字段（用户已确认）。

## 2. 冲突与重复清单

以下横切边界在多处重复（彼此一致，不矛盾，仅冗长），P1 收拢到 `AGENTS.md`「共享边界」：

| 边界 | 重复位置（代表性） |
| --- | --- |
| 不打分 / 不设能力等级 | `AGENTS.md`（五技能表 + 行为规则）、`docs/Quinn-Product-Contract.md` §1/§5/§6/§7、五个 `SKILL.md` 职责边界、`transfer-practice.md`、`jitou-training.md`、`shared/contracts.md` §10、`README.md` |
| 归属不变式（AI 提议不得默认 accepted） | `shared/contracts.md` §4、`session-format.md`、`mentor-interaction.md`、`transfer-practice.md`、`experience-reflection.md` |
| 不推断情绪 / 人格 / 动机 / 心理状态 | `mentor-interaction.md`、`experience-reflection.md`、`session-format.md`、`profile.md`、`AGENTS.md`、各扩展计划 |
| 不强制行动 / 目标 / 作业 | `mentor-interaction.md` 建议安全线、`session-format.md`、`quinn-synthesize/SKILL.md`、`quinn-explore/SKILL.md`、各扩展计划 |
| 不强制答完全部题目 | `quinn-brainstorming/SKILL.md`、`AGENTS.md`、`question-patterns.md`、`jitou-training.md` |

## 3. 误读点清单（P1 就地澄清，不改行为）

1. 「完整答案/完整方案（帮助等级 4 允许）」vs「不先写完整答案再让用户复述（禁止）」——完整答案可作为交付直接给出并标 AI 贡献，但不得作为要求用户复述的测试或能力证据。
2. 「完整资料报告（explore 不负责）」vs「research 产出带来源的 `workspace/research/` 记录」——不矛盾：explore 可引用，research 产记录。
3. 「0–4 帮助等级」vs 能力评分——0–4 是「给多少帮助」，映射 `assistance_level`，不是用户能力等级。
4. `evals/scenarios.md` 内部 0/1/2 打分——仅用于对照不同 Quinn 版本，不面向用户。
5. 「情绪」两用——经历复盘按用户原文记录；`mentor-interaction.md` 介入信号只决定是否澄清，均不诊断。

## 4. 命名对账（confirmation）

外部文档 `confirmation ∈ proposed/confirmed/corrected/rejected` 映射到现有枚举（不新增、不升 `schema_version`）：

| 外部 | 现有 |
| --- | --- |
| `proposed` | `candidate_reframe` / 「Quinn 候选」（`attribution=assistant`） |
| `confirmed` | `user_stance: accepted` 或经历复盘用户回应 `confirmed` |
| `corrected` | `revised`（经历复盘用户回应） |
| `rejected` | `user_stance: rejected` 或经历复盘用户回应 `rejected` |

## 5. Delta 清单（本次实际改动）

| Delta | 处理 | 位置 |
| --- | --- | --- |
| `help_direction` 字段 | 映射到现有，不新增 | 本文 §1 |
| 删除机制缺失（外部文档误判「已有删除机制」） | 新增 `scripts/workspace.py delete <kind> <id>` | P2 |
| 横切边界 12+ 处重复 | 收拢到 `AGENTS.md`「共享边界」，各 SKILL 引用 | P1 |
| 5 处可误读表述 | 就地加一句区分 | P1 |
| `corrected`→`revised` 命名 | 加映射注释 | P1 |

## 6. 范围与非目标

- 覆盖 P0（本映射）、P1（会话行为收口）、P2（删除机制 + 总结/恢复确认）。
- 不新增 `help_direction` 字段、不新增第六个 Skill、不引入 DSL/工作流引擎/情绪识别器/能力评分/独立画像库/自动提醒（外部文档 §8 暂缓项）。
- P3 小实验：已由 `transfer-practice`（迁移练习）、`jitou-training`（验证状态）、`quinn-practice`（训练闭环 + `application_reports`）覆盖，不重复实现。
- P4 真实会话验证：留待实际使用，仅本文标注。
- 旧 `topics/discussions/insights` 保持可读，不批量补字段。

## 7. 基线样本

对照样本（读不改）：`workspace/sessions/` 7 份真实会话 + `workspace/examples/session-cross-domain.md`。不额外收集个人信息。
