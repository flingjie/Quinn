---
id: insight-outcome-pricing
schema_version: "1"
revision: 1
created_at: "2026-09-11T09:00:00+00:00"
updated_at: "2026-09-11T09:00:00+00:00"
question: "按结果收费成立依赖什么？"
explanation: "至少依赖三个条件：结果可验收、可归因到产品、客户认可结果价值并愿付费。"
attribution: assistant
user_stance: partial
evidence_refs:
  - record_id: research-outcome-pricing
    source_id: s1
    relation: supports
boundaries: "仅针对能明确归因到产品的任务；通用助手类难以按结果收费。"
open_questions:
  - question: "客户付费意愿如何？"
    status: waiting
    observation_condition: "遇到实际合同或价格资料"
    review_date: null
history:
  - at: "2026-09-11T09:00:00+00:00"
    change: "首次形成认识"
    reason: "基于研究记录 research-outcome-pricing"
    evidence_refs:
      - record_id: research-outcome-pricing
        source_id: s1
        relation: supports
    user_quote: "我认可结果可验收的重要性，对客户付费意愿仍持保留态度。"
---

# 认识：按结果收费

> 示例记录（格式参照，非真实数据）。

- `attribution=assistant` + `user_stance=partial`：解释由 AI 提出，用户明确部分认可。
- 用户原话保留在 `history[].user_quote`，作为 `partial` 的证据，防止默认接受。
- `evidence_refs[].relation` 记录该证据对解释的关系（supports/contradicts/limits/inconclusive）。
