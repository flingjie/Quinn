# 训练证据视图与延迟检查（P2）

能力证据（SkillEvidence）是派生视图，不落库。由 `quinn-synthesize` 在用户问「我练得怎么样」「检查一下进步」、结束一次训练会话，或回访要现实应用结果时按需计算。只列证据，不合成一个分数或永久标签。

## 推导步骤

1. `find "<主题>" goals` 或 `read <goal_id>` 拿到目标。
2. `find "" training_sessions` 筛 `goal_id` 匹配的会话（或按 goal 的 `record_ids`）。
3. 对每个会话 `find "<会话id>" attempts` 拿 attempts；`find "<attempt id>" feedback` 拿对应 feedback。
4. 按 `assistance_level` 与 `evidence_kind` 分类，逐条列出（见下）。

## 状态短语

| 短语 | 依据 |
| --- | --- |
| `一次独立表现` | `application` attempt 且 `assistance_level=independent`，对应 feedback 有 `demonstrated` |
| `有提示时完成` | `application` attempt 且 `assistance_level∈{hinted,template}`，对应 feedback 有 `demonstrated` |
| `新场景表现记录` | `transfer` attempt（`task_variant_id` 记录改变的那一个条件），有可观察结果 |
| `证据不足` | 无可支撑上述任一的记录 |

每条附 attempt / feedback ID；同一 goal 可同时有多条。不把示范（`demonstrated`/`coauthored`）或任务协助算作独立表现；不自动推断永久掌握；单次业务结果不反推能力。

## 延迟检查（现实应用）

回访或用户说「上次练的我在实际里用了一下」时：

1. `find "" attempts` 找 `evidence_kind: transfer`（或 `application`）的 attempts，读目标与反馈。
2. 只问结果，不自答：实际用了没？发生在哪？结果怎样？
3. 有现实反馈 → 按 `skills/quinn-practice/references/training-records.md`「应用报告」协议写 `application_reports`（`provenance: user_report` / `external_feedback`，`application_status: reported`，observation/outcome 来自用户报告，不补造）。
4. 用户说还没用 → `application_status: not_reported`，不写成成功案例；不得把训练中的模拟任务写成实际执行。
