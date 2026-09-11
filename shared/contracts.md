# Quinn 共享契约（Contracts）

本文定义 Quinn 三个 Skill（research / explore / synthesize）共用的数据约定：记录如何存储、字段如何命名、归属与证据如何标记、谁负责写什么。三个 Skill 与 `scripts/workspace.py` 均以本文为唯一真源。

> 原则：可追溯（重要事实能找到来源）、归属清晰（作者主张 / AI 提议 / 用户判断三者不混）、不伪造（证据不足时保留未知）。任何一条都不允许"AI 提议经默认值变成用户已接受"。

## 1. 文件位置与命名

- 记录存 `workspace/<kind>/<id>.md`，`kind` ∈ `topics` / `research` / `discussions` / `insights` / `sessions`。
- `id` 为随机唯一标识（UUID），由脚本生成；**不以标题或中文名作文件名**，避免重名与引用失效。
- 文件由 YAML frontmatter（夹在 `---` 之间）+ Markdown 正文组成。frontmatter 为结构化元数据，正文为人类可读的转述、原文与说明。

## 2. 公共元数据

所有记录 frontmatter 必须包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 随机唯一 ID，等于文件名去 `.md` |
| `schema_version` | string | 契约版本，当前 `1` |
| `revision` | int | 从 1 起，每次 `update_record` 递增 |
| `created_at` | string | 创建时间，带时区 ISO 8601（如 `2026-09-11T14:00:00+08:00`） |
| `updated_at` | string | 最后修改时间，同上 |

时间统一存带时区 ISO 格式；展示时再适配用户时区。`updated_at` 由脚本在写入时刷新，不由 Skill 手写。

## 3. 对象字段

### Topic（专题）—— `workspace/topics/`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string | 专题名 |
| `aliases` | list[string] | 别名/同义关键词 |
| `scope` | string | 专题范围说明 |
| `record_ids` | list[string] | 关联记录 ID（research/discussion/insight） |
| `summary` | string | 当前认识摘要 |
| `open_questions` | list[OpenQuestion] | 下次可调查的问题（聚合自相关 insight） |

### Research（研究记录）—— `workspace/research/`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `question` | string | 本次研究问题 |
| `topic_ids` | list[string] | 所属专题 |
| `sources` | list[Source] | 来源记录 |
| `claims` | list[string] | 事实与来源主张（每条带 source_id 引用） |
| `disagreements` | list[string] | 主要分歧 |
| `unknowns` | list[string] | 关键未知 |
| `coverage` | string | 覆盖范围与缺口说明 |
| `discussion_directions` | list[string] | 两三个讨论方向 |

### Discussion（讨论记录）—— `workspace/discussions/`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `question` | string | 本次讨论焦点 |
| `research_ids` | list[string] | 引用的研究记录 |
| `turns` | list[Turn] | 对话回合（用户原文 + 分析） |
| `explanations` | list[string] | 有依据的解释 |
| `methods_used` | list[string] | 实际使用的方法名 |
| `opportunities` | list[string] | 机会假设 |
| `user_stance_summary` | string | 用户态度小结（可选） |

### Insight（认识）—— `workspace/insights/`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `question` | string | 认识所回答的问题 |
| `explanation` | string | 当前解释 |
| `attribution` | string | 归属，见 §4 |
| `user_stance` | string | 用户态度，见 §4 |
| `evidence_refs` | list[EvidenceRef] | 证据引用，见 §5 |
| `boundaries` | string | 边界与适用条件 |
| `open_questions` | list[OpenQuestion] | 开放问题 |
| `history` | list[HistoryEntry] | 修订历史，见 §7 |

### Session（会话位置）—— `workspace/sessions/`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `mode` | string | 当前执行的是哪个 Skill |
| `topic_ids` | list[string] | 相关专题 |
| `record_ids` | list[string] | 相关记录 |
| `status` | string | `active` / `paused` / `completed` / `save_failed` |
| `next_step` | string | 下一步要做什么（文本） |

## 4. 归属与态度枚举

`attribution`（谁提出的解释）：
- `source_author` —— 来源作者/机构的主张
- `assistant` —— AI 的推断或提议
- `user` —— 用户的判断或表态

`user_stance`（用户对这条解释的态度，不论解释由谁提出）：
- `accepted` —— 认可
- `partial` —— 部分认可（须注明范围）
- `withheld` —— 保留态度
- `rejected` —— 否定
- `unexpressed` —— 未表态（默认）

> 硬规则：
> - AI 提议（`attribution=assistant`）**不得经默认值变成 accepted**：无用户明确表态时 `user_stance` 保持 `unexpressed`。
> - 用户明确表态（`accepted`/`partial`/`withheld`/`rejected`）时，须在 `history[].user_quote` 保留原话作为依据，否则视为缺证据。
> - 归属不清时一律保留 `assistant`；只有归属会影响具体输出且无法从原文判断时，才向用户问一句。

## 5. 证据引用与来源

- `EvidenceRef` = `{ record_id: string, source_id: string, relation?: string }`。`record_id` 指向 research 记录，`source_id` 是该记录 `sources` 列表内的条目 id；`relation`（可选）为该证据对解释的关系，取值见下方"新证据对解释的关系"。证据引用不自动推出用户态度。
- `Source` 字段：`source_id`、`url`、`title`、`author`（可得时）、`published_at`（可得时）、`accessed_at`、`access_status`（`ok` / `partial` / `failed`）、`summary`。
- 来源摘要存短摘录或释义，**不默认存整篇版权内容**。同源转发不算独立支持；同一 URL 的时间变化保留观察版本。

新证据对解释的关系（存于 insight 的 `evidence_refs` 或历史说明）：
- `supports` —— 支持现有解释
- `contradicts` —— 与现有解释冲突
- `limits` —— 限制/收窄现有解释的适用范围
- `inconclusive` —— 尚不能判断

冲突时保留双方引用，标注时间、样本与口径差异，**不自动判用户改观点**。

## 6. 开放问题状态

`OpenQuestion` = `{ question, status, observation_condition?, review_date? }`。
- `status`：`exploring`（值得继续且有可调查路径）/ `waiting`（等指定证据）/ `settled`（当前需要已满足）。
- 转移：缺资料 `exploring→waiting`；满足 `exploring→settled`；遇到相关证据 `waiting→exploring`；反例/条件变化/用户要求 `settled→重开`。
- `settled` 不代表最终正确，与真假独立。`review_date` 可选，不默认建后台任务。

## 7. 修订历史

同一认识（insight）的修订在**同一文件内**追加历史并更新当前摘要，不新建文件覆盖。`HistoryEntry` 字段：`at`（时间）、`change`（改了什么）、`reason`（依据）、`evidence_refs`（来源引用）、`user_quote`（用户原文依据，可选）。

> 硬规则：关键用户表态原文不能被整理摘要覆盖，须在 `history` 的 `user_quote` 保留。

## 8. 写入责任

- `quinn-research` 写 research 记录。
- `quinn-explore` 写 discussion 记录（用户原文 + 分析）。
- `quinn-synthesize` 写 insight、更新 topic、关联 methods_used。
- 三个 Skill 都经同一辅助函数更新 session 位置（`update_record` 或专用 session 写入）。

## 9. 恢复与一致性

- 写入串行化：文件锁保护"版本检查→替换"区间；临时文件与目标同目录，写完后原子替换。
- 引用记录先落盘，再更新专题；中断时允许有未关联记录，但不允许引用尚不存在的记录。
- 重复执行用已保存的 `record_id` + `expected_revision`；版本冲突重新读取并合并，不静默覆盖。
- 保存失败明确说明哪些内容未保存，保留可重试结果；源数据与用户原文不在恢复中重生成。
