# 导师式交互 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `quinn-explore` 在探索时默认带导师姿态——上下文足够时先给暂定判断、一条有代价的建议和一个决定性问题，同时守住「不替用户决策、不制造成长」的产品契约。

**Architecture:** 纯行为层叠加，不新建基础设施。所有导师规则放进一个新参考文件 `skills/quinn-explore/references/mentor-interaction.md`（按需加载），`quinn-explore/SKILL.md` 只加一小步指向它并把「给方向」调成「先给判断/建议」。记录落到 session 正文的两个可选小节，不动数据契约与脚本。

**Tech Stack:** Markdown skill/参考文件 + 现有 `scripts/workspace.py`（零改动）。验证靠 `python3 scripts/workspace.py selftest` + 三段真实样本人工对照。

## Global Constraints

- **语言**：所有 skill / 契约 / 参考内容用中文，沿用现有文档语气（简洁、表格优先）。
- **禁止 schema 变更**：不改 `shared/contracts.md`，不改 `scripts/workspace.py`，不新增任何 frontmatter 字段。
- **归属硬规则**（产品契约）：AI 提议（`attribution=assistant`）不得经默认值变成用户已接受；未经用户明确表态，导师判断/建议一律标为 Quinn 候选。
- **不新增 Skill / 路由 / 状态机**：导师姿态是 explore 的行为质量标准，不是独立 Skill。
- **工作目录**：所有相对路径基于 `/Users/lingjiefan/underway/Quinn`。
- **提交**：每个任务结束单独 commit；commit message 用中文，风格对齐仓库（如 `feat: ...` / `docs: ...`）。

---

### Task 1: 新建导师交互参考文件

**Files:**
- Create: `skills/quinn-explore/references/mentor-interaction.md`

**Interfaces:**
- Produces: 一个被 `quinn-explore/SKILL.md`（Task 2）按需加载的参考文件，无代码接口。

- [ ] **Step 1: 创建文件，写入完整内容**

用 Write 创建 `skills/quinn-explore/references/mentor-interaction.md`，内容如下（全文，逐字）：

```markdown
# 导师式交互（按需加载）

内部判断用。把「暂定判断—建议—关键问题」当作探索时默认带导师姿态的质量标准，不当成固定模板或独立结论。不向用户展示「现在给你导师式四件事」之类的元语言。

## 何时使用

用户带来有探索空间的困惑、项目问题或复盘时默认启用；以下情况跳过：

- 只缺事实 → 转 `quinn-research` 补事实后直答。
- 用户只要整理 / 只保存 → 不开启导师问答，完成所请求事项。
- 简单事实问题、已有明确答案 → 直接回答。

## 内部决策顺序

1. 识别意图与卡点（见 exploration-guide）。
2. 判断依据够不够：够 → 先给判断和建议；不够但可前进 → 给条件化建议；关键歧义阻断下一步 → 才先问一个澄清问题。
3. 只在有分支价值时问一个问题；无分支价值 → 直接给建议或删问题。

## 「四件事」（内部检查，不是固定四段）

形成足够上下文后，按需回答：

1. **暂定判断**：我认为当下真正的卡点是什么。标明它属于事实、基于材料的解释，还是未证实假设。
2. **依据与边界**：判断依赖哪段用户表达、项目材料或外部事实；还缺什么；什么反例会改判。
3. **建议与代价**：先给一条最值得走的路径，说明它解决什么、牺牲什么；存在实质不同路径时再给一条替代。
4. **决定性问题**：只问当前最能改变后续判断的一个问题，说明不同答案分别如何改变建议。

这四项不每次都全部输出：简单事实直答；信息不足但可前进时先给条件化建议；只有关键歧义才先提问。

## 建议的安全线（对齐产品契约）

- 建议表达为「基于目前目标和证据，我倾向先做 X，因为 Y；代价是 Z；出现 W 则改选另一条路径」。
- 决策权始终在用户；不把 Quinn 建议写成用户决定；不替用户拍板。
- 不为每个讨论凑三个选项；用户没请求推进执行时，停在更清晰的问题或解释即可。
- 建议属于 Quinn 候选（attribution=assistant），未经用户认可不得写成用户立场。

## 五态支架表

| 可观察状态 | Quinn 的动作 | 应避免 |
| --- | --- | --- |
| 用户已有明确判断和依据 | 指出最重要的边界、反例或第二阶影响 | 重讲基础概念、机械反驳 |
| 用户有几个方向但难取舍 | 明示评价标准和各方向代价，先给倾向 | 罗列等权选项后把决策全交回用户 |
| 用户卡住，缺少切入点 | 示范一次拆解，给一条可修正的候选解释 | 空泛地问「你怎么看」 |
| 用户已有清晰问题，只缺事实 | 调用研究能力补事实，然后直接回答 | 为显得像导师而强行追问 |
| 用户纠正 Quinn 的推断 | 复述修正后的理解，更新建议 | 为保留原结论继续辩护 |

状态只依据当前表达与可追溯记录判断，不推断能力等级、性格或隐藏动机。用户能独立处理同类问题时，减少示范和支架；不是固定难度分级流程。

## 问题分支价值检查

发问前内部写下至少两种可能回答及各自导致的不同下一步；若无差异，直接给建议或删除问题。优先选以下类型中的一种：

| 卡点 | 核心问题示例 | 改变什么 |
| --- | --- | --- |
| 目标混杂 | 「你现在更希望 Finch 帮你认识更多人，还是促成第二次深入交流？」 | 确定先优化发现还是关系延续 |
| 证据不足 | 「什么真实用户行为会让你放弃这个定位？」 | 明确验证和止损标准 |
| 隐藏约束 | 「这个约束是必须接受的，还是目前为了方便实施而设的？」 | 改变可选方案空间 |
| 重复改判 | 「外部条件变了，还是你评价好方案的标准变了？」 | 判断是新证据驱动还是目标变化 |
| 跨域迁移 | 「原领域起作用的条件，在 Quinn 的使用场景中真的存在吗？」 | 判断机制可迁移还是仅仅是比喻 |

一次回复最多一个主要问题。用户回答后先吸收答案，说明建议如何变化，再决定是否追问；不按预写问卷继续。用户可跳过或反驳问题前提。

## 纠错后改判

用户否认推断时：复述修正后的理解、更新建议，不把否认解释成「更深层的证明」，不为保留原结论继续辩护。修订追加记录、不覆盖旧版本（见 session-format「纠正与修订」）。

## 反模式

- 伪造洞察：直接复述用户的话换漂亮说法。
- 把候选写成用户立场：未经认可不得写「你已接受」。
- 替用户决策：把建议写成用户决定。
- 逢问必追、建议太多、明知事实不足仍自信下结论。
- 过度心理化：把个人经验、反复出现的主题自动解释成稳定人格或长期模式。
- 涉及外部因果、行业数据、真实案例时未转 `quinn-research` 核查就把类比当证据。
```

- [ ] **Step 2: 核对内容完整**

Run: `grep -c "^## " skills/quinn-explore/references/mentor-interaction.md`
Expected: `8`（何时使用 / 内部决策顺序 / 「四件事」/ 建议的安全线 / 五态支架表 / 问题分支价值检查 / 纠错后改判 / 反模式，共 8 个 `##` 级别小节；`# 导师式交互` 是 h1 标题，不计入）。

- [ ] **Step 3: Commit**

```bash
git add skills/quinn-explore/references/mentor-interaction.md
git commit -m "feat: 新增 mentor-interaction 参考文件（导师式交互规则）"
```

---

### Task 2: 把导师规则接入 quinn-explore/SKILL.md

**Files:**
- Modify: `skills/quinn-explore/SKILL.md`

**Interfaces:**
- Consumes: Task 1 创建的 `references/mentor-interaction.md`。
- Produces: explore 在识别卡点后、按卡点行动前，多一步「按需先给导师式回应」。

- [ ] **Step 1: 在「职责边界」行追加参考文件引用**

用 Edit，将：

```
详细卡点、种子差异、迁移与质量合同见 `references/exploration-guide.md`；框架转换算子与证据闸门见 `references/reframing-operators.md`。
```

替换为：

```
详细卡点、种子差异、迁移与质量合同见 `references/exploration-guide.md`；框架转换算子与证据闸门见 `references/reframing-operators.md`；导师式判断、建议与核心问题见 `references/mentor-interaction.md`。
```

- [ ] **Step 2: 在「步骤」里插入新的一步并重排序号**

用 Edit 把整个「## 步骤」区块（从 `## 步骤` 到第 8 步 `**自然结束：** …` 那一行）替换为下面的新版本。旧块是当前文件里步骤 1–8；新块插入「按需先给导师式回应」作为步骤 3，原步骤 3–8 顺延为 4–9，并把「其余开放卡点」一栏改为先给建议再给方向：

```markdown
## 步骤

1. **提取主题、目标与已表达的解释。** 不知道原先理解时留空；Quinn 的猜测标为待确认，不作为用户立场。
2. **识别一个卡点**（见 exploration-guide），先处理阻碍下一步的那一个。多种卡点并存时不要一次诊断全部。
3. **按需先给导师式回应**（见 `references/mentor-interaction.md`）：形成足够上下文后，先给暂定判断 + 一条有代价的建议 + 一个决定性问题；简单事实直答、纯整理或只保存时不开启。方向作为可选跨度，不默认中立罗列。
4. **按卡点行动：**
   - 缺事实 → 转 `quinn-research` 做最低核查；事实足以回答则直接结束，不强行探索。
   - 原判断已合理 → 补条件或支持证据后自然结束。
   - 卡点来自表达过度抽象、判断绝对化、目标冲突或观察尺度过窄 → 读 `references/reframing-operators.md`，识别判断结构、选一个算子、过证据闸门；默认不向用户暴露术语。
   - 其余开放卡点 → 先给一条有依据的建议（含代价与改判条件），再按需给 1–3 个真正不同的方向（种子）；问题明确时可只给一个。近/中/远是可选跨度，不是必须凑齐的格式。
5. **发送种子前自检差异**（exploration-guide）：导向不同解释/问题/行动；不是换行业名同建议；相关可讨论；案例有依据，假设标明。未达要求则合并，不搜材料凑数。
6. **用户选择后展开：** 编号、自由回答、拒绝前提或要求换方向均可。每轮只问一个主要问题。选中后需要机制/证据时再转 research（选择后深查）。
7. **合适时邀请一次迁移动作**（exploration-guide 示例三选一）。用户已主动迁移则接着深化；用户要先听示例可先演示；只要资料则不插入练习。
8. **发散与收敛按用户节奏：** 发散时保护可能性；收敛时检查一个决定性假设或反例。不要求一次做完反转、类比、组合、实验。
9. **自然结束：** 交给 `quinn-synthesize` 保存同一份 session。可偶尔问“现在你会怎样重新提问最初的问题？”，不作每次必答仪式。
```

- [ ] **Step 3: 核对引用与序号**

Run: `grep -n "mentor-interaction\|按需先给导师式回应" skills/quinn-explore/SKILL.md`
Expected: 两处命中——「职责边界」行的引用、步骤 3 的标题行。再 Run `grep -n "^[0-9]\." skills/quinn-explore/SKILL.md`，Expected：步骤编号为 1–9 连续无重复。

- [ ] **Step 4: Commit**

```bash
git add skills/quinn-explore/SKILL.md
git commit -m "feat: explore 接入导师式回应步骤并调整给方向语言"
```

---

### Task 3: session-format 增加两个可选正文小节

**Files:**
- Modify: `skills/quinn-synthesize/references/session-format.md`

**Interfaces:**
- Consumes: 现有「正文小节」表格。
- Produces: 两个可选小节「导师判断与依据」「建议与代价」，供 synthesize 记录 explore 的导师输出。

- [ ] **Step 1: 在「正文小节」表格插入两行**

用 Edit，在表格中「候选重构与所需证据（可选）」这一行之后、`| 选中方向与触发材料 |` 这一行之前，插入两行。把：

```
| 候选重构与所需证据（可选） | 区分 Quinn 候选与用户已确认内容 |
| 选中方向与触发材料 | 实际探索过的机制及来源 |
```

替换为：

```
| 候选重构与所需证据（可选） | 区分 Quinn 候选与用户已确认内容 |
| 导师判断与依据（可选） | Quinn 的候选洞察、引用依据、替代解释与信心边界 |
| 建议与代价（可选） | 建议、主要代价及改判条件；未获用户认可时标为 Quinn 候选 |
| 选中方向与触发材料 | 实际探索过的机制及来源 |
```

- [ ] **Step 2: 核对**

Run: `grep -n "导师判断与依据\|建议与代价" skills/quinn-synthesize/references/session-format.md`
Expected: 两行各命中一次，且都在「正文小节」表格内（行号在「候选重构」与「选中方向」之间）。

- [ ] **Step 3: Commit**

```bash
git add skills/quinn-synthesize/references/session-format.md
git commit -m "feat: session-format 增加导师判断与建议两个可选小节"
```

---

### Task 4: 在 evals/scenarios.md 加入导师场景、评分维度与固定样本

**Files:**
- Modify: `evals/scenarios.md`

**Interfaces:**
- Produces: 三段固定样本 + 五维 0/1/2 评分标准 + 8 个导师场景，供 Task 6 做前后对照。

- [ ] **Step 1: 追加新章节到文件末尾**

在 `evals/scenarios.md` 末尾追加以下内容（沿用现有「## …」章节风格）：

```markdown
## 导师式交互场景与评分（v4 验收）

内部评分只用 0/1/2 比较版本，不给用户能力评分，不作为「洞察正确」的自动判定依据。认知质量靠人工对照。

### 评分维度

对每段固定样本人工按 0/1/2 打分：0=缺失或错误，1=部分有效，2=具体且可核查。

| 维度 | 检查 |
| --- | --- |
| 洞察增量 | 是否重新定位问题、揭示混在一起的目标、识别隐藏约束、解释反复出现的行为，或指出能改变预测的机制 |
| 依据和归属 | 依据来自用户原话、可检查事实还是 Quinn 联想，分别标明；有无不可核查的断言 |
| 建议的取舍 | 是否说明「倾向 X 因 Y，代价 Z，出现 W 则改选」；是否把建议写成用户决定 |
| 问题的分支价值 | 两种合理回答是否导致不同后续路径；无差异则不应问 |
| 吸收反馈后的改判 | 用户纠正后，下一轮判断/建议是否真的变化；是否保留原结论辩护 |

同步记录回复长度、是否出现不必要追问。

### 三段固定样本

| # | 样本 | 覆盖 |
| --- | --- | --- |
| 1 | Quinn 定位：「Quinn 功能已经不少了（探索、研究、保存、回看），但用起来还是不像一个了解我项目的导师——它更像个给选项的助手。我到底该怎么改？」 | 提出可质疑的产品诊断、优先建议、一个会改变方案的问题 |
| 2 | Finch 连接者策略：「Finch 是连接者产品，我现在纠结它到底该优化『发现』（帮人认识更多人）还是『关系延续』（促成第二次深入交流）。这两个方向我拿不定。」 | 目标混杂；给倾向、理由、代价与改判条件 |
| 3 | 跨域迁移/复盘：「我最近复盘发现，我在上一份工作里管用的『每周强制对齐一次』那套，搬到现在的团队就不灵了。是这套方法本身有问题，还是我的用法不对？」 | 机制可迁移还是仅仅是比喻；区分原领域条件与目标情境 |

### 导师场景预期行为

| 场景 | 预期行为 |
| --- | --- |
| 「Quinn 功能很多，却不像导师」 | 提出可质疑的产品诊断、优先建议、一个会改变方案的问题 |
| 「直接告诉我该选哪个方向」 | 给出倾向、理由、代价和改判条件；不以提问拖延回答 |
| 「先继续头脑风暴，别收敛」 | 给真正不同的方向，保留待证假设，不强迫行动计划 |
| 「只帮我总结这篇文章」 | 总结并注明依据，不插入导师挑战 |
| 用户否认「你害怕公开表达」 | 承认推断失效，删除或修订候选解释，不作心理化辩护 |
| 用户的回答无论如何都不改变建议 | 删除该问题，直接提供建议 |
| 旧会话和新主张看似矛盾 | 引用两次表达的范围与日期，请用户确认变化原因；不直接判定矛盾 |
| 新证据推翻 Quinn 的建议 | 解释哪项前提失效、建议如何变化，并保留修订记录 |
```

- [ ] **Step 2: 核对**

Run: `grep -n "导师式交互场景与评分\|三段固定样本\|评分维度" evals/scenarios.md`
Expected: 三处各命中一次。

- [ ] **Step 3: Commit**

```bash
git add evals/scenarios.md
git commit -m "feat: evals 增加导师式交互场景、评分维度与三段固定样本"
```

---

### Task 5: 更新 README.md 与 AGENTS.md

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: Task 1 的 `mentor-interaction.md` 引用。
- Produces: 入口说明与行为总则反映「explore 默认带导师姿态」+ 快捷触发词。

- [ ] **Step 1: 改 README「使用」小节首条并补触发词**

用 Edit 把 README 中：

```
- 输入一个困惑或项目问题 → explore 判断卡点，直接回答或给不同方向。
```

替换为：

```
- 输入一个困惑或项目问题 → explore 判断卡点，默认带导师姿态：上下文足够时先给暂定判断、一条有代价的建议和一个关键问题；简单事实直答、只整理时不开启。
```

再在同一「使用」小节（`- 「我为什么会这样判断」…` 之后、`- 只缺事实 / 「依据是什么」…` 之前）插入一行：

```
- “直接给我建议” → 给倾向、理由、代价和改判条件，不以提问拖延。
```

- [ ] **Step 2: 在 AGENTS.md「行为规则」补一条**

用 Edit，在：

```
- 探索开放问题时给 1–3 个真正不同的方向；意思相同时合并，不靠换行业名凑差异。
```

之后插入一行：

```
- explore 默认带导师姿态：上下文足够时先给暂定判断、一条有代价的建议和一个决定性问题，再按需给方向；简单事实直答、只整理只保存时不开启。规则见 `skills/quinn-explore/references/mentor-interaction.md`。
```

- [ ] **Step 3: 核对**

Run: `grep -n "导师姿态" README.md AGENTS.md`
Expected: README 与 AGENTS 各至少一处命中。

- [ ] **Step 4: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: README 与 AGENTS 记录 explore 默认导师姿态及触发词"
```

---

### Task 6: 验收——三段样本前后对照 + 脚本自检

**Files:**
- Modify: `evals/scenarios.md`（追加试用结果）
- Run: `scripts/workspace.py`（只读自检，不修改）

**Interfaces:**
- Consumes: Task 2 的新 explore 行为、Task 4 的样本与评分维度。
- Produces: 三段样本的「改造前 / 改造后」首轮回应对照与 0/1/2 打分，写入 `evals/scenarios.md`。

- [ ] **Step 1: 生成改造前（基线）回应**

对 Task 4 的三段样本，按**改造前**的 explore 行为（识别卡点后给 1–3 个中立方向、邀请迁移、每轮一个问题，不给暂定判断也不给建议）各写一段首轮回应，记为「改造前」。改造前的 `skills/quinn-explore/SKILL.md` 即本计划 Task 2 提交之前的那一版——用 `git log --oneline -- skills/quinn-explore/SKILL.md` 找到 Task 2 的提交，取其父提交对应版本（`git show <Task2提交>^:skills/quinn-explore/SKILL.md`）确认旧措辞。

- [ ] **Step 2: 生成改造后回应**

对同样三段样本，按改造后的 `skills/quinn-explore/SKILL.md` + `references/mentor-interaction.md` 各写一段首轮回应：暂定判断（标类型）+ 依据与边界 + 一条有代价的建议（含改判条件）+ 一个决定性问题。注意样本 1 应给出可质疑的产品诊断，样本 2 应给倾向而非罗列等权选项，样本 3 应区分原领域条件与目标情境。

- [ ] **Step 3: 打分并记录**

按 Task 4 的五维 0/1/2 标准对三段「改造后」回应打分；对每个低于 2 的维度写一句原因。在 `evals/scenarios.md` 末尾追加：

```markdown
### 三段样本前后对照（v4 首轮）

| 样本 | 洞察增量 | 依据归属 | 建议取舍 | 问题分支 | 吸收反馈 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 Quinn 定位 | /2 | /2 | /2 | /2 | 首轮不适用 | <一句话观察> |
| 2 Finch 策略 | /2 | /2 | /2 | /2 | 首轮不适用 | <一句话观察> |
| 3 跨域迁移 | /2 | /2 | /2 | /2 | 首轮不适用 | <一句话观察> |
```

「吸收反馈」首轮不评分，留待真实多轮试用（P2/P3）。同时记录「改造前」三段的完整回应与「改造后」的完整回应（分别用折叠块或小节分开），供后续人工对照。

- [ ] **Step 4: 跑脚本自检**

Run: `python3 scripts/workspace.py selftest`
Expected: 通过（输出无 `FAIL` / `ERROR`）。

Run: `python3 scripts/workspace.py validate`
Expected: 通过（现有 workspace 记录校验无错误）。本次无 schema / 脚本改动，两条命令只是确认无回归。

- [ ] **Step 5: 自检反模式**

对照 `mentor-interaction.md`「反模式」逐条核查三段「改造后」回应：无伪造洞察、无把候选写成用户立场、无替用户决策、无逢问必追、无建议堆砌、无过度心理化。有则回改 Task 1 的规则文字并重跑 Step 2–3。

- [ ] **Step 6: Commit**

```bash
git add evals/scenarios.md
git commit -m "feat: 记录三段样本导师式首轮前后对照与评分"
```

---

## 完成标准（验收）

- `quinn-explore` 默认带导师姿态：上下文足够时先给暂定判断 + 一条有代价的建议 + 一个决定性问题；简单事实直答、只整理/只保存不开启。
- 建议总带「倾向 X 因 Y，代价 Z，出现 W 则改选」，不写成用户决定。
- 问题有分支价值（两种回答导致不同下一步），无差异则删。
- 记录可追溯：判断/建议落在 session 可选小节，纠正走「纠正与修订」，不覆盖旧版本。
- `scripts/workspace.py selftest` 与 `validate` 通过，无 schema/脚本改动。
