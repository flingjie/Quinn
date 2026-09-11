---
name: quinn-synthesize
description: 整理讨论成果、总结专题、比较新旧认识、回顾观点，并把认识持久化。当用户说"整理一下""今天到这里"、想总结一个专题、比较新旧认识、回顾某个观点、或在一轮研究/讨论后收尾时使用。
---

# quinn-synthesize

整理刚才讨论、总结专题、比较新旧认识、回顾某观点。

职责边界：产出"这次新增或改变了什么、未解决什么、关联记录、后续观察条件"。整理允许无变化；不制造"成长"，不强迫观点更新，不要求用户填写表单。

## 步骤

1. **读全相关记录**：读取需要综合的完整研究/讨论/认识记录（`python3 scripts/workspace.py read <id>`），不只根据摘要推定用户态度。
2. **找变化与矛盾**：新增机制、差异、矛盾、反例；合并重复的开放问题。
3. **整理认识记录**：区分归属——来源作者（`source_author`）、AI 提议（`assistant`）、用户判断（`user`）。
4. **处理用户新表态**：有新的用户表态时更新其观点并在 `history` 保留旧版本与原话；无表态时只增加建议和证据，不改 `user_stance`。
5. **关联方法**：把实际用过的方法关联到案例（`methods_used`），无需复制完整方法介绍。
6. **更新专题**：更新 topic 摘要与下次可调查的问题。

## 归属硬规则（shared/contracts.md §4、§7）

- AI 提议不得经默认值变成 accepted；无用户明确表态时 `user_stance` 保持 `unexpressed`。
- 用户明确表态（`accepted`/`partial`/`withheld`/`rejected`）时，须在 `history[].user_quote` 保留原话作为依据，关键表态原文不可被摘要覆盖。
- 归属不清时保持 `assistant`；只有归属影响具体输出且无法从原文判断时才问一句。

## 持久化

认识写 `workspace/insights/<id>.md`（以下命令从项目根目录运行）：

```bash
cat > /tmp/quinn-insight.yaml <<'EOF'
question: "<认识回答的问题>"
explanation: "<当前解释>"
attribution: assistant          # source_author / assistant / user
user_stance: unexpressed        # accepted/partial/withheld/rejected 需 history[].user_quote 依据
evidence_refs:
  - record_id: "<研究记录ID>"
    source_id: "<该记录内的 source_id>"
    relation: supports          # supports / contradicts / limits / inconclusive（可选）
boundaries: "<边界与适用条件>"
open_questions:
  - question: "<开放问题>"
    status: exploring           # exploring / waiting / settled
    observation_condition: "<什么证据能推进，可空>"
history:
  - at: "<ISO 时间>"
    change: "<改了什么>"
    reason: "<依据>"
    evidence_refs: []
    user_quote: "<用户原话依据，可空>"
body: |
  <Markdown 正文：认识、证据、边界>
EOF
python3 scripts/workspace.py create insights /tmp/quinn-insight.yaml
```

**更新已有认识**（追加历史、保留旧版本）：先 `python3 scripts/workspace.py read <insight_id>` 取得当前 revision，再 `python3 scripts/workspace.py update <insight_id> <revision> <payload>`（payload 含新的 `explanation`、追加的 `history` 项）。版本冲突则重读合并，不静默覆盖。

**更新专题**：同法 update 对应 topic 的 `summary`、`record_ids`、`open_questions`。

**会话位置**：用 `sessions` 记录保存当前 `mode` / `record_ids` / `status` / `next_step`；暂停只保存现场，不强迫完成总结。

## 输出与结束反馈

输出：这次新增或改变了什么、未解决什么、关联记录、可选后续观察条件。

结束反馈三段：本次形成的认识、仍未解决的分歧、已保存且下次可继续的问题。没有观点认可就写"暂定解释"或"AI 建议"。

完成标准：能从专题追溯观点及依据，并支持下一次研究。
