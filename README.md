# Quinn

从真实困惑出发的探索伙伴：接触不同解释与跨领域机制，共同形成新理解、开放问题和可选机会。默认从探索开始；需要事实时再研究；结束时保存真实发生的理解变化。

AI 是主要应用落点，也允许完全非 AI 的探索。跨领域、前提反转、机制重组是手段，不为了展示方法强行使用。

## 三个 Skill

通过自然语言触发（无需显式指定技能名）：

| Skill | 用途 | 触发示例 |
| --- | --- | --- |
| `quinn-explore` | 理解困惑、给不同方向、按需换框架、共同迁移 | “帮我想想这个问题”“换个框架看这件事” |
| `quinn-research` | 查证事实、找机制与反例 | “依据是什么”“帮我核实这个说法” |
| `quinn-synthesize` | 保存收获、恢复会话、对比理解 | “记下这个问题”“继续上次的……” |

## 使用

直接对话即可。典型入口：

- 输入一个困惑或项目问题 → explore 判断卡点，默认带导师姿态：上下文足够时先给暂定判断、一条有代价的建议和一个关键问题；简单事实直答、只整理时不开启。
- “给我一个值得想的问题” → 按显式兴趣找少量异常，核实后提供入口。
- “换个更远的角度” → 扩大领域距离，保持与原问题关联。
- “换个框架看这件事” → 识别判断结构，选一个最相关的转换动作。
- “我为什么会这样判断” → 澄清证据标准、隐含准则和优先级，不进行心理诊断。
- “直接给我建议” → 给倾向、理由、代价和改判条件，不以提问拖延。
- 只缺事实 / “依据是什么” → research 查证后可直接结束，不强行跨域。
- “记下这个问题” / “整理一下” → synthesize 保存同一份会话后结束。
- “继续上次的……” → 读取相关会话，复述一句上下文后接着讨论。

无需每次输出实验或走完固定流程。允许确认原判断、暂无变化或只有开放问题。

## 目录

- `skills/` —— 三个 Skill 的规范源（`.claude/skills` 与 `.codex/skills` 均符号链接到这里）。
- `shared/contracts.md` —— 数据契约（字段、归属、证据、来源规则）。
- `shared/methods/` —— 方法参考（按需读取）。
- `scripts/workspace.py` —— 文件操作脚本（创建/读取/更新/查找/校验）。
- `workspace/` —— 持久化目录（会话为主；研究按需；个人记录不入库，见 `workspace/README.md`）。
- `evals/` —— 行为场景与试用对照。
- `docs/` —— 设计文档。
- `AGENTS.md` —— Agent 行为总则。

## 依赖

Python 3 + PyYAML（`pip install pyyaml`），仅 `scripts/workspace.py` 需要。

## 参考

产品契约：`docs/Quinn-Product-Contract.md`（唯一产品真源）  
主线实现方案：`docs/Quinn-Cross-Domain-Exploration-Implementation-Plan.md`  
数据契约：`shared/contracts.md`  
历史方案：`docs/Quinn-Research-Strategy-Implementation-Plan.md`
