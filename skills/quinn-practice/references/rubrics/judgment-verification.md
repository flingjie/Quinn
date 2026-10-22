# judgment-verification（判断验证）v1

task_ref: `judgment-verification`  
current_version: `v1`

目标：判断的结论不超证据，处理反证，能提出区分竞争解释的验证动作。复用 `mentor-interaction.md`「结果复盘三问」。

## 可观察标准

| criterion_id | 标准 | 可观察定义 |
| --- | --- | --- |
| `jv-claim` | 结论清楚，并说明成立条件/假设 | 结论有明确范围，不绝对化 |
| `jv-evidence` | 依据强度与结论匹配，结论不超证据 | 结论范围 ≤ 证据支持范围 |
| `jv-counter` | 识别或回应最不符合结论的反例 | 至少处理一个反证/反例 |
| `jv-test` | 提出能区分竞争解释的最小验证动作 | 具体可执行，非泛泛「再调研」 |

## verdict 含义

- `demonstrated`：标准可观察成立，且有 `source_quote`。
- `needs_work`：可观察到缺口，`source_quote` 指向缺口处。
- `insufficient_evidence`：依据不足、无法判断（合法无引用）。

## 正/反例

- `jv-evidence` 正例：「样本仅覆盖华东、且为 6 月数据，所以结论只能限定为『华东 6 月』，不推广到全国。」
- `jv-evidence` 反例（needs_work）：「这个产品一定能火」——无依据、结论超证据。
