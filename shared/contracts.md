# Quinn 共享契约（Contracts）

本文定义 Quinn 三个 Skill（research / explore / synthesize）共用的数据约定：记录如何存储、字段如何命名、归属与证据如何标记、谁负责写什么。三个 Skill 与 `scripts/workspace.py` 均以本文为唯一真源。

> 原则：可追溯（重要事实能找到来源）、归属清晰（作者主张 / AI 提议 / 用户判断三者不混）、不伪造（证据不足时保留未知）。任何一条都不允许"AI 提议经默认值变成用户已接受"。理解变化必须依据用户表达；模型总结未经用户支持时标为候选，不得写成用户立场。

## 1. 文件位置与命名

- 记录存 `workspace/<kind>/<id>.md`，`kind` ∈ `topics` / `research` / `discussions` / `insights` / `sessions`。
- `id` 为随机唯一标识（UUID），由脚本生成；**不以标题或中文名作文件名**，避免重名与引用失效。
- 文件由 YAML frontmatter（夹在 `---` 之间）+ Markdown 正文组成。frontmatter 为结构化元数据，正文为人类可读的转述、原文与说明。
- 显式偏好另存 `workspace/profile.md`（非 kind，非脚本管理；无文件视为空偏好）。

## 2. 公共元数据

所有记录 frontmatter 必须包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 随机唯一 ID，等于文件名去 `.md` |
| `schema_version` | string | 契约版本，当前 `1`（由脚本写入；新语义用可选字段与正文，不升全局版本号） |
| `revision` | int | 从 1 起，每次 `update_record` 递增 |
| `created_at` | string | 创建时间，带时区 ISO 8601（如 `2026-09-11T14:00:00+08:00`） |
| `updated_at` | string | 最后修改时间，同上 |

时间统一存带时区 ISO 格式；展示时再适配用户时区。`updated_at` 由脚本在写入时刷新，不由 Skill 手写。

## 3. 对象字段

### Topic（专题）—— `workspace/topics/`

旧路径保留，可读可写；**默认探索闭环不再更新**。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string | 专题名 |
| `aliases` | list[string] | 别名/同义关键词 |
| `scope` | string | 专题范围说明 |
| `record_ids` | list[string] | 关联记录 ID（research/discussion/insight） |
| `summary` | string | 当前认识摘要 |
| `open_questions` | list[OpenQuestion] | 下次可调查的问题 |

### Research（研究记录）—— `workspace/research/`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `question` | string | 本次研究问题 |
| `topic_ids` | list[string] | 所属专题（可空） |
| `sources` | list[Source] | 来源记录 |
| `claims` | list[string] | 事实与来源主张（每条带 source_id 引用） |
| `disagreements` | list[string] | 主要分歧 |
| `unknowns` | list[string] | 相关未知 |
| `coverage` | string | 覆盖范围与缺口说明 |
| `discussion_directions` | list[string] | 可选；默认探索不要求凑方向，可 `[]` |

正文应区分：**事实** / **类比** / **假设**。

### Discussion（讨论记录）—— `workspace/discussions/`

旧路径保留；**默认探索闭环不再创建**。字段仍为：`question`、`research_ids`、`turns`、`explanations`、`methods_used`、`opportunities`、`user_stance_summary`。

### Insight（认识）—— `workspace/insights/`

旧路径保留；**默认探索闭环不再创建**。字段仍为：`question`、`explanation`、`attribution`、`user_stance`、`evidence_refs`、`boundaries`、`open_questions`、`history`。用户明确要求整理旧认识时仍可使用。

### Session（探索会话）—— `workspace/sessions/`

**主记录。** 一次探索维护一份；重复保存更新同一 ID。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `mode` | string | 当前主 Skill |
| `topic` | string | 短标题，供恢复检索（可选） |
| `topic_ids` | list[string] | 相关专题（可空） |
| `record_ids` | list[string] | 相关其他记录（可空） |
| `research_ids` | list[string] | 本次实际读过的研究记录（可选） |
| `status` | string | 见下方 status |
| `change_status` | string | 理解变化状态（可选） |
| `next_step` | string | 下一步 / 继续位置（文本） |

`status`：`exploring` / `paused` / `closed`；为兼容旧记录亦接受 `active` / `completed` / `save_failed`。status 不驱动执行；`closed` 不等于结论正确。

`change_status`：`expressed`（用户已表达变化）/ `original_confirmed`（确认原判断）/ `no_change`（暂无变化）/ `unconfirmed`（尚未确认）。兴奋或继续追问不是理解提升的证据。

正文按需小节见 `skills/quinn-synthesize/references/session-format.md`。

## 4. 归属与态度枚举

`attribution`（谁提出的解释）：
- `source_author` —— 来源作者/机构的主张
- `assistant` —— AI 的推断或提议
- `user` —— 用户的判断或表态

`user_stance`（用户对这条解释的态度，不论解释由谁提出；主要用于旧 insight 路径）：
- `accepted` —— 认可
- `partial` —— 部分认可（须注明范围）
- `withheld` —— 保留态度
- `rejected` —— 否定
- `unexpressed` —— 未表态（默认）

> 硬规则：
> - AI 提议（`attribution=assistant`）**不得经默认值变成 accepted**：无用户明确表态时 `user_stance` 保持 `unexpressed`。
> - 用户明确表态（`accepted`/`partial`/`withheld`/`rejected`）时，须在 `history[].user_quote` 保留原话作为依据，否则视为缺证据。
> - 归属不清时一律保留 `assistant`；只有归属会影响具体输出且无法从原文判断时，才向用户问一句。
> - Session 正文中的「当前理解」必须区分用户表达与 Quinn 候选总结。

## 5. 证据引用与来源

- `EvidenceRef` = `{ record_id: string, source_id: string, relation?: string }`。`record_id` 指向 research 记录，`source_id` 是该记录 `sources` 列表内的条目 id；`relation`（可选）为该证据对解释的关系，取值见下方。证据引用不自动推出用户态度。
- `Source` 字段：`source_id`、`url`（或文档标识）、`title`、`author`（可得时）、`published_at`（可得时）、`accessed_at`、`access_status`（`ok` / `partial` / `failed`）、`summary`（支持的主张摘要）。
- 来源摘要存短摘录或释义，**不默认存整篇版权内容**。同源转发不算独立支持；同一 URL 的时间变化保留观察版本。

新证据对解释的关系：
- `supports` —— 支持现有解释
- `contradicts` —— 与现有解释冲突
- `limits` —— 限制/收窄现有解释的适用范围
- `inconclusive` —— 尚不能判断

冲突时保留双方引用，标注时间、样本与口径差异，**不自动判用户改观点**。

## 6. 开放问题状态

`OpenQuestion` = `{ question, status, observation_condition?, review_date? }`（insight/topic 结构化字段）。Session 正文中的开放问题可用列表叙述，回访时由 synthesize 选取其中一个。

- `status`：`exploring` / `waiting` / `settled`。
- `settled` 不代表最终正确。`review_date` 可选，不默认建后台任务。

## 7. 修订历史

同一认识（insight）的修订在**同一文件内**追加历史并更新当前摘要。`HistoryEntry`：`at`、`change`、`reason`、`evidence_refs`、`user_quote`。

Session 的纠正与后续证据在**同一 session 文件**正文追加，不覆盖变化历程；通过 `update_record` 递增 revision。

> 硬规则：关键用户表态原文不能被整理摘要覆盖。

## 8. 写入责任

- `quinn-research` 写 research 记录。
- `quinn-explore` 引导探索；**不再默认写 discussions**。
- `quinn-synthesize` 写/更新 **session**（主记录）；负责恢复、纠正、回访与 profile 显式偏好更新。
- 用户明确要求时，synthesize 仍可写 insight / 更新 topic（旧路径）。
- 三个 Skill 经同一脚本更新记录；重复保存不新建 session。

## 9. 恢复与一致性

- 写入串行化：文件锁保护"版本检查→替换"区间；临时文件与目标同目录，写完后原子替换。
- 引用记录先落盘，再更新引用方；中断时允许有未关联记录，但不允许引用尚不存在的记录。
- 重复执行用已保存的 `record_id` + `expected_revision`；版本冲突重新读取并合并，不静默覆盖。
- 保存失败明确说明哪些内容未保存，保留可重试结果；源数据与用户原文不在恢复中重生成。
- 恢复会话：按主题、ID 或近期 `find` 结果读取最少相关 session，先复述一句上下文再继续。
