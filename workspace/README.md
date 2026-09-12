# Workspace

Quinn 的持久化目录：探索会话与研究材料以「YAML frontmatter + Markdown 正文」的文件形式存在这里。字段定义见 `shared/contracts.md`（唯一真源）。

## 目录结构

| 路径 | 用途 | 版本控制 |
| --- | --- | --- |
| `sessions/` | **主记录**：探索会话、理解变化、继续位置 | gitignore（个人数据） |
| `research/` | 按需研究材料及来源 | gitignore |
| `topics/` | 专题摘要（旧路径，默认探索不再更新） | gitignore |
| `discussions/` | 旧讨论记录（默认探索不再创建） | gitignore |
| `insights/` | 旧认识记录（默认探索不再创建） | gitignore |
| `profile.md` | 用户明确说过的偏好及来源（非 kind） | gitignore |
| `examples/` | 可复现示例记录（格式参照） | 纳入版本控制 |

## 记录如何创建

**不要手工写 kind 记录文件**。由 `scripts/workspace.py` 生成 ID、校验字段、做版本化与原子写入：

```bash
python3 scripts/workspace.py create sessions /tmp/payload.yaml
python3 scripts/workspace.py create research /tmp/payload.yaml
python3 scripts/workspace.py read <id>
python3 scripts/workspace.py update <id> <revision> /tmp/payload.yaml
python3 scripts/workspace.py find "<关键词>" [kind]
python3 scripts/workspace.py validate
python3 scripts/workspace.py selftest
```

payload 为 YAML/JSON（保留键 `body` 放正文）。`find` 结果含 `updated_at`，便于恢复近期会话。更多用法见脚本 docstring。

`profile.md` 不是 kind：由 synthesize 在用户明确表态时直接读写；格式见 `examples/profile.md`。

三个 Skill（`skills/quinn-*`）负责生成 payload 并调用脚本，不直接操作 kind 文件。

## 示例

`examples/` 下含 outcome-pricing（旧五类记录）与 `session-cross-domain.md`（新探索会话）、`profile.md`（偏好格式）。真实记录由脚本分配 UUID。
