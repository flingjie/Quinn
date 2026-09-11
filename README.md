# Quinn

围绕 AI、Agent、AIGC 与 Token 经济的研究与策略思考伙伴：搜集资料、理解机制、学习方法、讨论解释并发现机会。AI 先整理必要材料，用户参与思考和观点形成。

## 三个 Skill

Quinn 由三个可独立使用的 Skill 组成，通过自然语言触发（无需显式指定技能名）：

| Skill | 用途 | 触发示例 |
| --- | --- | --- |
| `quinn-research` | 研究主题、整理链接、找资料、查证说法 | "帮我查一下按结果收费的案例" |
| `quinn-explore` | 讨论商业逻辑、解释方法、分析想法 | "这个产品想法靠不靠谱？" |
| `quinn-synthesize` | 整理讨论、总结专题、比较新旧认识 | "整理一下，今天到这里" |

## 使用

直接对话即可。典型流程：

- 给一个链接、只要求整理 → research 保存有来源的材料。
- 带着材料想讨论 → explore；结束时说"整理一下" → synthesize。
- 回顾已有专题 → synthesize；缺证据时给调查建议，不默认大范围搜索。

## 目录

- `skills/` —— 三个 Skill 的规范源（`.claude/skills` 与 `.codex/skills` 均符号链接到这里）。
- `shared/contracts.md` —— 数据契约（字段、归属、证据、来源规则）。
- `shared/methods/` —— 方法参考（按需读取）。
- `scripts/workspace.py` —— 文件操作脚本（创建/读取/更新/查找/校验）。
- `workspace/` —— 持久化目录（研究、讨论、认识、专题、会话；个人记录不入库，见 `workspace/README.md`）。
- `docs/` —— 设计文档。

## 依赖

Python 3 + PyYAML（`pip install pyyaml`），仅 `scripts/workspace.py` 需要。

## 参考

设计与验收标准：`docs/Quinn-Research-Strategy-Implementation-Plan.md`
