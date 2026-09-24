---
name: quinn-synthesize
description: 简短收获、保存或更新探索会话、区分真实理解变化与候选总结、恢复上下文与回访开放问题。当用户说整理一下、记下这个问题、今天到这里、继续上次、纠正记录，或探索自然结束需要落盘时使用。
---

# quinn-synthesize

简短收获、会话记录、理解变化与恢复上下文。

职责边界：保存实际发生的内容；允许无变化；不制造“成长”，不强迫观点更新，不自动推断稳定人格，不强制行动计划。格式细节见 `references/session-format.md`。

## 步骤

1. **判断动作：** 新建保存 / 更新同一 session / 恢复继续 / 用户纠正 / 回访开放问题 / 主动选题入口（见下）。
2. **读最少相关记录：** 用 `find` / `read`，不全量加载历史。已知 ID 直接 `read`。
3. **整理收获：** 新认识、开放问题、确认的原判断，或尚无变化。区分用户已表达 vs Quinn 候选总结。
4. **写入或更新一份 session**（主记录）。有研究材料时写入 `research_ids`，材料本身仍在 `workspace/research/`。
5. **默认不再** `create insights` 或更新 topics。用户明确要求整理旧专题/认识时，仍可按 `shared/contracts.md` 读写 insights/topics（旧路径保留）。

## 保存 / 更新

首次保存：

```bash
cat > /tmp/quinn-session.yaml <<'EOF'
mode: explore
topic: "<短标题>"
topic_ids: []
record_ids: []
research_ids: ["<研究记录ID，可空>"]
status: closed
change_status: unconfirmed
next_step: "<一句继续位置，可空>"
body: |
  ## 原问题
  <用户原话或标明转述>

  ## 原先理解
  <仅用户已表达；未知则写「未表达」>

  ## 原判断与类型
  <可选；保留原文，类型是可纠正的内部标记>

  ## 候选重构与所需证据
  <可选；区分 Quinn 候选与用户已确认内容>

  ## 选中方向与触发材料
  <实际探索的机制与来源>

  ## 用户迁移
  <用户自己的推导；无则省略本节>

  ## 当前理解
  - 用户表达：...
  - Quinn 候选总结：...（未经用户认可时不得写成用户立场）

  ## 开放问题
  - ...

  ## 后续证据或行动
  <发生后追加，不预填成功>

  ## 继续位置
  <下次从哪里接上>
EOF
python3 scripts/workspace.py create sessions /tmp/quinn-session.yaml
```

重复保存或暂停后续写：先 `read` 取得 `revision`，再 `update` **同一 ID**，禁止再 `create`。版本冲突则重读合并，不静默覆盖。写失败须明确说明未保存内容，不得声称成功。

`status`：`exploring` / `paused` / `closed`（旧值 `active` / `completed` / `save_failed` 仍合法）。`change_status`：`expressed` / `original_confirmed` / `no_change` / `unconfirmed`。

空小节省略。不保存冗长内部推理。

## 恢复会话（P2）

用户说“继续上次的……”或点名主题/ID 时：

1. `python3 scripts/workspace.py find "<关键词>" sessions`（结果含 `updated_at`，优先近期命中）。
2. 只 `read` 一两份最相关记录。
3. 先复述**一句**上下文：选中方向 + 继续位置（或开放问题）。
4. 再接着讨论；不要重播整份总结。
5. 无法确定是哪一次会话时，简短澄清一句。

对比原先理解与当前理解；允许 `no_change` / `unconfirmed`。用户纠正记录时**追加**说明，不覆盖变化历程，不把未说的话写成用户立场。后续证据追加到同一 session 正文，并更新 `research_ids`。

## 回访与主动选题（P3）

- **回访：** 用户要求回访或带来新线索时，从相关 session 选**一个**开放问题；引入新证据或新问题，不重放旧结论。需要核查时转 research。
- **主动选题：** 用户说“给我一个值得想的问题”时，读 `workspace/profile.md`（若存在）中的显式兴趣，并用 `find` 看近期 sessions，避免重复同一结论或只推荐熟悉领域；找少量异常，核实后交给 explore 作为入口。
- **兴趣纠正：** 只改 profile 里用户明确说过的条目及来源；不推断性格、能力或稳定认知习惯。无 profile 文件则当空偏好。

## Profile

路径：`workspace/profile.md`（个人文件，不入库）。格式见 `workspace/examples/profile.md`。不是 `workspace.py` 的 kind；用普通文件读写。只记录明确偏好及其来源。

## 输出

本次新增或改变了什么（或明确无变化）、未解决什么、session ID、下次可继续的位置。

结束反馈宜短：认识或确认、开放问题、已保存且可继续的一点。没有用户表态就写“暂定 / Quinn 候选”，不写成用户已接受。
