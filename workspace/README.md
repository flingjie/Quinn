# Workspace

Quinn 的持久化目录：研究、讨论与认识都以「YAML frontmatter + Markdown 正文」的文件形式存在这里。字段定义见 `shared/contracts.md`（唯一真源）。

## 目录结构

| 路径 | 用途 | 版本控制 |
| --- | --- | --- |
| `topics/` | 专题摘要与相关记录引用 | gitignore（个人数据） |
| `research/` | 每次研究材料及来源 | gitignore |
| `discussions/` | 用户原文、分析和阶段记录 | gitignore |
| `insights/` | 认识、证据、边界与修订历史 | gitignore |
| `sessions/` | 继续位置与任务引用 | gitignore |
| `examples/` | 可复现示例记录（格式参照） | 纳入版本控制 |

## 记录如何创建

**不要手工写记录文件**。由 `scripts/workspace.py` 生成 ID、校验字段、做版本化与原子写入：

```bash
python3 scripts/workspace.py create research /tmp/payload.yaml
python3 scripts/workspace.py read <id>
python3 scripts/workspace.py update <id> <revision> /tmp/payload.yaml
python3 scripts/workspace.py find "<关键词>" [kind]
python3 scripts/workspace.py validate
python3 scripts/workspace.py selftest
```

payload 为 YAML/JSON（保留键 `body` 放正文）。更多用法见脚本 docstring。三个 Skill（`skills/quinn-*`）负责生成 payload 并调用脚本，不直接操作文件。

## 示例

`examples/` 下是一组可复现示例（按结果收费主题），演示五种记录类型与交叉引用。它们使用可读 ID，仅供格式参照；真实记录由脚本分配 UUID。
