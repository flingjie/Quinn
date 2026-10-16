# Notion 日记材料（只读）

用户把日记存在 Notion（Notes 容器 → 月度页 → toggle 块，标题「M月D日 + 主题」）。
Quinn 只读日记作为探索「材料」，不写回。

## 何时用

用户说「看最近一周日记」「聊聊这条日记」「从日记里找点东西探索」等，把日记当材料时。

## 用法

```bash
# 列出最近 N 天日记（JSON；--days 覆盖 config 的 notion_lookback_days）
python3 scripts/notion.py list-diary --days 7

# 读某条正文（默认剥掉 Finch 讨论记录区；--with-discussion 才带上）
python3 scripts/notion.py read <block_id>

# 核对 Notes 容器可访问性（只读）
python3 scripts/notion.py doctor
```

- 凭据 `NOTION_API_KEY` 读环境变量或仓库根 `.env`；`notes_page_id` / `lookback_days` 读 `workspace/config.md`。
- `list-diary` 返回字段：`block_id`、`title`、`created_at`、`page_id`、`url`。

## 材料归属

- 日记条目是「材料」，session 正文记录 `block_id + 标题 + url` 作为来源；不把日记内容默认标成已证实事实（用户自述）。
- 结论仍由 synthesize 写 `workspace/sessions/`，不写回 Notion。
