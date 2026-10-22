# 训练记录写协议

本技能单写 `goals` / `training_sessions` / `attempts` / `feedback` 四 kind，经 `scripts/workspace.py`。字段与枚举真源是 `shared/contracts.md` §10，此处只写写入顺序与语义。

## 写入顺序（引用先落盘）

goal → training_session → attempt → feedback。脚本 `_check_references` 强制：引用记录先存在，再写引用方。

## 状态机

- `goals`：`draft → active → {completed, archived}`；创建须 `draft`；`active → completed` 需 `record_ids` 非空（指向证据）。
- `training_sessions`：创建须 `draft`；白名单见 `shared/contracts.md` §10（`draft → active → awaiting_attempt / awaiting_application → reviewed`，允许 `paused` / `cancelled`）。`reviewed` 表示完成本次整理，不等于目标达成；后续会话是共享 `goal_id` 的 NEW `training_sessions`。

## Attempt 不可变

`attempts` 正文 = 用户产物逐字保留，不被反馈覆盖。`workspace.py` 对 `attempts` 的 `update` 直接拒绝；修改须新建 attempt。

## assistance_level 与 0–4 帮助等级映射

实时「给多少帮助」用 `mentor-interaction.md` 的 0–4（不落库）；每次尝试实际用到什么落库为 `assistance_level`：

| 0–4 帮助 | assistance_level |
| --- | --- |
| 0（一个关键问题，不额外提示） | `independent` |
| 1（一个提示 / 缩小范围） | `hinted` |
| 2/3（两个方向 / 局部示范） | `template` |
| 4（完整示范） | `demonstrated`（用户实质修改则 `coauthored`） |

`assistance_details` 始终记录实际用到的提示/示范（`{type, ref, note}`），多种帮助并存保留明细，不只记一个等级。

## 证据来源派生

不单独存 provenance 字段；由 `assistance_level` 派生：`independent`→user_artifact，`hinted`/`template`→user_artifact-with-help，`demonstrated`→model_demo，`coauthored`→mixed。这从视图层保证「模型示范不算 user_artifact」「任务协助不算独立证据」。

## 证据类型

`evidence_kind`：`understanding`（复述/反例）/ `application`（当前任务实际运用）/ `transfer`（换条件，P2）。改写同一题 = 同 `task_variant_id` 新 attempt = 修订，不是迁移。

## rubric 版本

`training_sessions.rubric_version` 开会话时固定，`feedback.rubric_version` 反馈时写同一版本；历史反馈绑定当时版本，改 rubric 不重写旧反馈。
