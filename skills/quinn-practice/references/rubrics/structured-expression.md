# structured-expression（结构化表达）v1

task_ref: `structured-expression`  
current_version: `v1`

目标：让听者在汇报/方案/问题描述里快速知道「当前问题、依据、需要决定什么」。

## 可观察标准

| criterion_id | 标准 | 可观察定义 |
| --- | --- | --- |
| `se-goal` | 开头一句话说清「当前问题 + 需要听者做的决定」 | 第一句含现状与明确请求/决定点 |
| `se-structure` | 各部分关系清楚（问题→依据→方案/建议） | 有顺序或因果/取舍关系，非并列罗列 |
| `se-evidence` | 关键判断有依据，区分事实与解释 | 依据可定位，事实与解释不混 |
| `se-ask` | 结尾有明确下一步请求或决定点 | 有具体「需要谁做什么」 |

## verdict 含义

- `demonstrated`：该标准可观察成立，且有 `source_quote`。
- `needs_work`：可观察到缺口，`source_quote` 指向缺口处。
- `insufficient_evidence`：材料不足、无法判断（合法无引用）。

## 正/反例

- 正例开头：「现状是 Q3 转化率下降 12%，我判断主因是渠道变化，需要你们今天定是否砍 A 渠道。」
- 反例开头（`se-goal` needs_work）：「我来说一下最近的情况，主要有几个方面……」——无现状、无决定请求。
