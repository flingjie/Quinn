# 每日商业判断训练器

帮助技术型构建者在信息不完整时，判断一门生意是否值得推进，理解商业逻辑、成本、风险和利润，并说明「什么证据会改变我的选择」。

核心实现：**一个教练式 Skill + 案例文件 + 训练记录**。多轮对话，关键位置停下等用户；先独立判断、再被一次实质挑战、再更新、再反馈。

## 目录结构

```text
business-judgment-trainer/
  skill/                         # 平台无关的核心指令与参考文件
    SKILL.md                     # 教练指令（单一事实源）
    references/
      rubric.md                  # 评分锚点 + 能力等级
      case-template.md           # 案例模板 + 人工验收清单
      review-template.md         # 复盘格式
  cases/                         # 题目（每题 brief.md + coach.md）
    index.json                   # 题目元数据与顺序
    case_001/ … case_004/
  sessions/                      # 训练记录（由 Skill 写入）
```

平台入口（薄封装，指向 `skill/SKILL.md`）：

- Claude Code：`.claude/skills/business-judgment-practice/SKILL.md`
- Codex：`.codex/skills/business-judgment-practice/SKILL.md`

## 如何使用

在支持的环境里调用 `business-judgment-practice` 这个 Skill，然后用自然语言表达意图：

| 说 | 发生什么 |
| --- | --- |
| 「开始今天的练习」或指定题目 | 启动训练 |
| 「继续上次练习」 | 读取未完成记录并从下一步继续 |
| 「复盘最近的训练」 | 汇总表现、证据、暂定等级和一个后续重点 |

## 当前题目（启动包）

| ID | 主维度 | 训练内容 |
| --- | --- | --- |
| case_001 | 成本 | AI 服务中的人工交付成本 |
| case_002 | 商业逻辑 | 使用意愿与付费意愿 |
| case_003 | 利润 | 收入、获客费用与盈亏边界 |
| case_004 | 成本 | 不同软件服务中的实施和维护成本（case_001 变式） |

## 边界

本版不包含自动抓取案例、动态课程引擎、数据库、自动等级升级或排行榜。训练记录为 JSON 文件，由 Skill 直接写入；出现保存摩擦后再按需补最小工具（见设计文档「阶段 B」）。

设计文档：`docs/Daily-Business-Judgment-Trainer-MVP-Implementation-Plan.md`
