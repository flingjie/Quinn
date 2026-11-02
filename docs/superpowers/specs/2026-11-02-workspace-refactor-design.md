# workspace.py 内部重构设计：拆分 selftest + 声明式校验

日期：2026-11-02
状态：已批准待实现
类型：零行为变化的内部重构

## 背景与目标

`scripts/workspace.py` 当前 1047 行，其中 `_selftest` 约 320 行（31%），`_collect_issues` 是逐 kind 的长 if/elif 链（约 80 行）。两者使文件偏大、校验逻辑难扩展：新增 kind 或字段枚举时必须修改分支逻辑。

目标：

1. 把 selftest 拆到独立文件，核心脚本收缩到约 720 行。
2. 枚举/必填类校验改为声明式规则表驱动，新增 kind 只加表项、不改逻辑。
3. `validate_workspace` 第二遍引用检查复用第一遍的解析结果，去掉重复 open + parse。

**硬约束：对外行为零变化。** CLI 命令、公开函数签名、校验规则、错误信息文案全部保持逐字一致。

## 变更内容

### 1. 拆分 selftest

- 新建 `scripts/workspace_selftest.py`：承载原 `_selftest` 的全部用例，`import workspace` 后调用其公开函数（`create_record` / `read_record` / `update_record` / `delete_record` / `find_records` / `validate_workspace`）与所需私有助手（`_record_path`、`_kind_dir`）。
- `scripts/workspace.py` 的 `selftest` 子命令保留，内部 `import workspace_selftest` 并委托执行。调用方式 `python3 scripts/workspace.py selftest` 完全不变，输出格式（`✓` 行、清理提示、通过/失败汇总）不变。
- 用例一条不删、一条不改。

### 2. 声明式校验规则表

新增模块级常量 `KIND_RULES`，形如：

```python
KIND_RULES = {
    "sessions": {
        "enums": {"status": SESSION_STATUSES, "change_status": CHANGE_STATUSES},
        "required": (),
    },
    "goals": {
        "enums": {"status": GOAL_STATUSES},
        "required": ("desired_behavior",),
    },
    "training_sessions": {
        "enums": {"status": TRAINING_STATUSES, "delivery_mode": DELIVERY_MODES},
        "required": ("goal_id",),
    },
    "attempts": {
        "enums": {"assistance_level": ASSISTANCE_LEVELS, "evidence_kind": EVIDENCE_KINDS},
        "required": ("session_id",),
    },
    "feedback": {
        "enums": {},
        "required": ("attempt_id", "rubric_version"),
    },
    # topics / research / discussions / insights 无 kind 专属枚举，走通用项
}
```

`_collect_issues` 重构为三段：

1. **通用项**：`attribution`、`user_stance` 枚举校验，对所有 kind 生效（现状如此）。
2. **规则表**：按 `KIND_RULES[kind]` 检查枚举合法性（值非 None 且不在枚举中则报错）与必填非空。
3. **跨字段特例函数列表**：规则表无法表达的留为小函数，逐个调用——
   - `user_stance` 为表态值时 `history[].user_quote` 必须存在；
   - sessions 的 `period_start` / `period_end` 日期格式；
   - feedback 的 `criterion_results[].verdict` 枚举及 `demonstrated`/`needs_work` 需 `source_quote`；
   - attempts 的 `assistance_details[].type` 枚举；
   - 通用嵌套项：`open_questions[].status`、`sources[].access_status`、evidence `relation`。

**错误信息文案逐字保持现状**（selftest 与使用方依赖这些提示语），包括字段名、枚举排序展示（`sorted(...)`）与中文说明。

### 3. validate_workspace 去重复解析

第一遍遍历时把 `(kind, record_id) -> fm` 缓存在内存；第二遍引用完整性检查直接用缓存，删除重新 `open` + `_parse_file` 的代码。输出的 issues 列表与顺序不变。

## 不做的事

- 不改任何枚举值、状态机白名单、入口态规则。
- 不改 CLI 参数、输出 JSON 结构。
- 不动 `notion.py`、`shared/contracts.md`、各 SKILL 文档。
- 不引入新依赖（保持标准库 + PyYAML）。
- 不迁移或冻结旧 kind（topics / discussions / insights 行为不变）。

## 验证标准

1. 重构前记录基线：`python3 scripts/workspace.py selftest` 全部通过；`python3 scripts/workspace.py validate` 对现有真实记录的输出存档。
2. 重构后：selftest 全部通过（用例数不少于基线）；`validate` 输出与基线逐字一致。
3. 随机抽查错误路径：非法枚举、缺必填、非法状态转换的报错文案与基线一致。
