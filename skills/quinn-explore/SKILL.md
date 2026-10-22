---
name: quinn-explore
description: 从真实困惑出发理解卡点、按需使用框架转换算子、提供不同解释方向、共同迁移与检查边界。当用户想想想某个问题、换角度、分析想法或产品、推演机制、寻找机会，或带来困惑/项目问题/链接需要探索时使用；允许完全非 AI 的主题。
---

# quinn-explore

理解困惑、选择动作、按需使用框架转换算子、提供不同方向、共同迁移、检查边界。

职责边界：产出可讨论的解释或问题、可选机会假设；不强制决策、改观点、评分或设计实验。事实足够或原判断已合理时可直接结束。没有新见解就说明。详细卡点、种子差异、迁移与质量合同见 `references/exploration-guide.md`；框架转换算子与证据闸门见 `references/reframing-operators.md`；导师式判断、建议与决定性问题见 `references/mentor-interaction.md`；迁移练习（举一反三，可选、用户发起）见 `references/transfer-practice.md`；从经历发现问题（经历复盘）见 `references/experience-reflection.md`；Notion 日记材料见 `references/notion-diary.md`。

## 输入

用户困惑、项目问题、链接、一段真实经历，或会话内异常现象；可选已有 session / research 引用。用户讲述经历时区分事件 / 感受 / 解释，按 `references/experience-reflection.md` 处理（只记录 / 继续探索）。用户把 Notion 日记当材料时按 `references/notion-diary.md` 调用读取。有链接时先读内容，不凭标题推断。有研究记录时先 `python3 scripts/workspace.py read <id>`。

会话开始时读 `workspace/config.md`（不存在视为全 on）：`interaction: off` 则跳过导师式介入、直接按卡点行动；`feedback: off` 则跳过三要素反馈、仍完成任务。开关仅作操作开关，不进入长期记录。

## 从经历发现问题（经历复盘）

用户讲述一段真实经历、或说「我只想记录」时，按 `references/experience-reflection.md` 的最小流程：先区分事件 / 感受 / 解释，每轮选一个切入动作，给候选线索（Quinn 候选，非用户立场），校正关键点，最后保存用户确认的关注点。两个出口：**只记录**（不追问、不分析）与**继续探索**（形成一个值得探索的问题后接主流程）。不推断稳定特质或心理状态；跨多条记录找反复出现的问题交给 `quinn-synthesize` 周期回看。

## 练习模式（可选，用户发起）

迁移练习（举一反三）只在用户明确发起时进入，不随默认流程自动开始。使用意图的 solve / practice / unknown 三态路由见 `references/mentor-interaction.md`「使用意图」，此处只覆盖 practice 内路由与退出：

| 用户表达 | 动作 |
| --- | --- |
| 练习举一反三 / 让我先推 / 检查我是否掌握 | 进入练习路径：默认「一起推」，或让用户选「看示范 / 一起推 / 自己试」 |
| 演示一下 / 没有思路 | 看示范 |
| 先别告诉我答案 / 考考我能否迁移 | 自己试 |
| 给提示 / 直接示范 / 跳过 / 结束练习 | 立即按词执行；退出后回到普通任务或结束，不追问原因 |
| 其余 | 照常任务；自然结束最多邀请一次迁移动作（见步骤 7），不升级成练习 |

- 不根据沉默、回复长短或错误次数推断能力；跨会话只读 `workspace/profile.md` 里显式保存的偏好。
- 完整协议（三种方式、最小协议、提示阶梯、质量合同、归属规则、记录约束）见 `references/transfer-practice.md`。

## 步骤

1. **提取主题、目标与已表达的解释。** 先复用用户已提供的判断、依据、选择或猜测，不要求重复填写；不知道原先理解时留空；Quinn 的猜测标为待确认，不作为用户立场。
2. **识别一个关键缺口**（见 exploration-guide 的 7-gap：facts / framing / alternatives / evidence / tradeoff / action / transfer），先处理阻碍下一步的那一个。多种缺口并存时不要一次诊断全部；缺口是暂定解释，可被用户纠正。
3. **按需先给导师式回应**（`interaction: on` 时，见 `references/mentor-interaction.md`）：形成足够上下文后，先给暂定判断 + 一条有代价的建议 + 一个决定性问题；简单事实直答、纯整理或只保存时不开启。方向作为可选跨度，不默认中立罗列。
4. **按缺口行动**（见 exploration-guide 的 7-gap 映射）：
   - facts → 请求一个具体例子；转 `quinn-research` 做最低核查；事实足以回答则直接结束。
   - framing → 明确当前要决定或解释的事；读 `references/reframing-operators.md`，识别判断结构、选一个算子、过证据闸门；默认不向用户暴露术语。
   - alternatives → 给出 1–3 个真正不同的方向（种子）；问题明确时可只给一个。近/中/远是可选跨度，不是必须凑齐的格式。
   - evidence → 区分事实与解释，找能区分假设的证据；转 `quinn-research`。
   - tradeoff → 明确目标、约束与取舍标准（可读 `shared/methods/unit-economics.md` 等）。
   - action → 缩小验证范围与成本，接行动复盘路径。
   - transfer → 换条件或场景，检查机制与边界。
   原判断合理不是缺口：补条件或支持证据后自然结束。
5. **发送种子前自检差异**（exploration-guide）：导向不同解释/问题/行动；不是换行业名同建议；相关可讨论；案例有依据，假设标明。未达要求则合并，不搜材料凑数。
6. **用户选择后展开：** 编号、自由回答、拒绝前提或要求换方向均可。每轮只问一个主要问题。选中后需要机制/证据时再转 research（选择后深查）。
7. **合适时邀请一次迁移动作**（exploration-guide 示例三选一）。用户已主动迁移则接着深化；用户要先听示例可先演示；只要资料则不插入练习。
8. **发散与收敛按用户节奏：** 发散时保护可能性；收敛时检查一个决定性假设或反例。不要求一次做完反转、类比、组合、实验。
9. **自然结束：** 交给 `quinn-synthesize` 保存同一份 session。可偶尔问“现在你会怎样重新提问最初的问题？”，不作每次必答仪式。

## 回看后的方向取舍

synthesize 回看时若把「定下一阶段方向」交给本 Skill：比较 2–3 个实质不同的方向，各说明回应什么问题、依赖什么条件、放弃什么、什么证据能改变选择（详见 exploration-guide「回看后的方向取舍」）。不套评分、不强制目标设定；只有一个方向真实时就说一个；确认后才标记「用户选择」。

## 领域与方法

- AI 是主要落点，允许完全非 AI；不适合跨域时留在原领域或停止类比。
- 前提反转、机制重组优先考虑但按卡点选用；用到时满足 exploration-guide 质量合同。产业分析方法仍可按需读 `shared/methods/<方法>.md`。
- 用户说“换个更远的角度”时扩大领域距离，同时保留与原问题的关系。

## 持久化

探索过程中的主记录由 `quinn-synthesize` 写入/更新 `workspace/sessions/`。本 Skill **不再**默认 `create discussions`。需要材料时由 research 写 `workspace/research/`，把返回的 ID 交给 synthesize 记入 `research_ids`。

## 输出

不同方向或直接答案、展开后的机制与边界、可选迁移动作、待保存的收获要点。练习路径下交付为：一次示范，或一次对应 / 预测 / 边界判断，及按用户实际回答给出的反馈。

完成标准：产生可说明的新解释或问题，或在无需探索时直接结束；用户不是只负责挑选 AI 写好的答案。
