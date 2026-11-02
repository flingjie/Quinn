# Quinn 只读 Notion 日记接入设计

日期：2026-10-16
状态：已确认，待写实施计划

## 1. 背景与现状核查

用户希望 Quinn 能读自己在 Notion 里的日记（最近一周）作为探索的「材料」，并参照 Finch 项目已有的 Notion 接入方式。本设计据此为 Quinn 增加一个**只读**的 Notion 日记读取能力。

核查到的两个事实：

**Finch 的 Notion 接入（参照对象）**
- 直连 `api.notion.com/v1`，标准库 `urllib`，不引第三方 HTTP 依赖。
- 只读写页面与块（page / block children），不碰数据库（database）。
- 素材以 toggle 块存在月度页，只追加不重写；写侧另有本地缓存 + 待同步队列。
- 凭据 `NOTION_API_KEY` 放 `.env`；`notes_page_id` / `parent_page_id` 放本地 YAML。

**用户的 Notion 日记（已实际读取确认）**
- 结构：Notes 容器页 → 年份页（2024、2025）+ 月度页（`2026.1` … `2026.10`）→ toggle 块。
- 一条日记 = 一个 toggle 块，标题「M月D日 + 主题」，正文为段落。
- 最近一周（10/9–10/16）共 6 条，内容形态不统一：成段反思、两行速记、链接＋要点摘要均有；个别已带 Finch 追加的「Finch 讨论记录」区。
- 标题里的日期与 block 的 `created_time` 一致。

结论：日记是纯 pages/blocks 结构，Quinn 只读不需要 Finch 之外的任何新能力（尤其不需要 database 查询）。

## 2. 设计决定（已与用户确认）

| 分叉 | 决定 | 理由 |
| --- | --- | --- |
| 接入方向 | **只读，作探索输入** | 日记是「材料」，结论仍由 synthesize 存 `workspace/sessions/`，不写回 Notion |
| 落地路线 | **移植只读脚本进 Quinn（路线 B）** | 只读场景用不到 Finch 的写队列/字段映射；贴合 Quinn「skills + 确定性脚本、无 src 包、无 CLI」的轻量架构 |
| 传输层 | **照抄 Finch**（urllib + Bearer + `Notion-Version`） | 已验证可用，零第三方 HTTP 依赖 |
| 「最近一周」判定 | **按 block 的 `created_time` 过滤** | 机器可读、可靠；避免解析中文日期字符串（标题是用户约定，可能漂移） |
| skill 归属 | **并入 `quinn-explore`，不新增第 4 个 skill** | 符合 AGENTS.md「三种能力归位、不新增 Skill」 |

## 3. 范围

### 改动的文件

| 文件 | 改动 |
| --- | --- |
| `scripts/notion.py` | **新建**：只读 Notion 脚本，子命令 `list-diary` / `read` / `doctor` / `selftest` |
| `.env`（Quinn 根，gitignore） | **新建**：`NOTION_API_KEY`（密钥不进仓库） |
| `.gitignore` | 加 `.env`（当前未忽略） |
| `workspace/config.md`（本地，gitignore） | 加 `notion_notes_page_id`、`notion_lookback_days` 两行 |
| `skills/quinn-explore/references/notion-diary.md` | **新建**：何时调用、命令用法、材料归属 |
| `skills/quinn-explore/SKILL.md` | 「输入」段加一句 Notion 日记来源并指向参考文件 |

### 不改动

- `shared/contracts.md`、`scripts/workspace.py`：无 schema 变更；日记材料不新建 kind。
- 三个 Skill 的职责边界；不新增独立 Notion skill。
- Finch 仓库：不 import、不改动、不抽共享包。

## 4. 数据流

```
用户说「看最近一周日记 / 聊聊这条日记」
  → quinn-explore 判断卡点
  → 缺材料时：python3 scripts/notion.py list-diary --days 7
        [从 notes_page_id BFS 发现月度页 → 收集 toggle 块 → 按 created_time 过滤近 N 天]
        → 输出 JSON：[{block_id, title, created_at, page_id}]
  → 选中某条：python3 scripts/notion.py read <block_id>
        [读该 toggle 的 children，剥掉「Finch 讨论记录」区]
        → 输出正文纯文本（用户原始日记）
  → 作为「材料」进入 explore 正常流程
  → 结论仍由 synthesize 写 workspace/sessions/
```

## 5. 组件设计

### 5.1 `scripts/notion.py`（确定性只读脚本）

- 传输照抄 Finch：标准库 `urllib` + `Authorization: Bearer <key>` + `Notion-Version: 2022-06-28`，不引第三方 HTTP 依赖。
- 四个子命令：
  - `list-diary [--days N]` — BFS 发现 `notes_page_id` 下所有月度页，收集 toggle 块，按 `created_time` 过滤近 N 天（默认 7），输出 JSON 列表。
  - `read <block_id>` — 读该 toggle 的 children；默认只返回用户原始正文（剥掉 `Finch 讨论记录 #disc_xxx` 标记起的追加区，复用 Finch 用户区/Finch 区分割逻辑的读侧）；`--with-discussion` 才带上 Finch 讨论区。
  - `doctor` — 只读核对 `notes_page_id` 可访问性。
  - `selftest` — 离线自检：用录好的 JSON fixture 校验「发现 + created_time 过滤 + 用户区剥除」解析逻辑，对齐 `workspace.py` 的 `selftest` 惯例。
- 错误处理对齐 Finch：把 `HTTPError` / 超时 / `URLError` 统一映射为带状态码的 `NotionError`；key 缺失或 page_id 未配置时明确报错，不伪造成功。

### 5.2 配置

- `NOTION_API_KEY` → 环境变量 / Quinn 自己的 `.env`（env-first，对齐 Finch）。
- `workspace/config.md`（本地、gitignore）加两行平铺 `key: value`：

  ```
  notion_notes_page_id: <用户 Notes 容器页 id>
  notion_lookback_days: 7
  ```

  `lookback_days` 同时可被 `--days` 覆盖。实际 page id 只进本地 gitignored 文件，不进版本控制。

### 5.3 `quinn-explore` 接入

- 在 `SKILL.md`「输入」段加一条 Notion 日记来源，并新增 `references/notion-diary.md`（按需加载）说明：何时调用、`list-diary`/`read` 用法、以及**材料归属**。
- 材料归属：日记条目作为「材料」时，在 session 正文记录 `block_id + 标题 + 页面 URL` 作为来源，遵循 `shared/contracts.md` 的来源归属原则，不新建 schema、不把日记内容默认标成已证实事实。

## 6. 明确不做（YAGNI）

- 不写回、不建本地缓存 / 待同步队列 / 同步操作日志（Finch 写侧全部不要）。
- 不碰数据库（database）。
- 不 import Finch、不抽共享包。
- 不做「全文归档到本地」——每次实时读。

## 7. 测试与验收

- `python3 scripts/notion.py selftest`：离线校验发现 / 过滤 / 剥除逻辑。
- 真实冒烟：`list-diary --days 7` 返回最近一周日记；`read <block_id>` 返回去掉讨论区的用户原文。
- 一次端到端：从日记条目触发 `quinn-explore`，session 正文正确记录 `block_id + 标题 + URL` 来源。
- 回归：`python3 scripts/workspace.py selftest` 确认未破坏现有写入。

## 8. 分阶段

- **P0**：已完成（Finch 参照与日记结构核查，见 §1）。
- **P1**：新建 `scripts/notion.py`（含 `selftest`）；加 `.env` 与 `.gitignore`；`workspace/config.md` 加两行；真实冒烟跑通 `list-diary` / `read`。
- **P2**：新建 `references/notion-diary.md` 并在 `quinn-explore/SKILL.md` 加输入来源；一次端到端日记探索验证材料归属。
- **P3**：真实使用中校准 `lookback_days` 与输出形态；确认无额外需要的读取命令。

详细实施步骤由 writing-plans 展开。
