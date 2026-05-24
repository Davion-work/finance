---
name: doc-structure
description: 通用项目文档架构规范。用于新项目初始化文档结构、已有项目文档结构审查与对齐、docs 子目录新增/删除/重命名时的同步操作。当用户说"初始化文档结构"、"对齐文档规范"、"加一个 docs 子目录"、"文档结构审查"等场景时使用。
last-updated: 2026-05-24
---

# 通用项目文档架构规范

## 适用范围

本 skill 定义所有项目统一的文档目录结构与维护规则，适用于：

- 新项目初始化文档骨架
- 已有项目的文档结构审查与对齐
- `docs/` 子目录的新增、删除、重命名操作
- AI 会话恢复时定位各类文档

---

## 标准目录结构

```
<project-root>/
├── README.md                          # 项目总入口：是什么、怎么用、怎么开发
├── CHANGELOG.md                       # 版本变更日志
│
├── docs/                              # 项目文档根目录
│   ├── README.md                      # 文档地图：一句话说明每个子目录的定位
│   │
│   ├── design/                        # 架构与设计决策
│   │   └── *.md                       # 整体架构、子系统设计、技术选型 ADR
│   │
│   ├── specs/                         # 需求/功能设计 spec（实现前的分析）
│   │   └── *.md                       # 每个 spec 一个文件，实现后归档保留
│   │
│   ├── guides/                        # 面向使用者的指南/手册
│   │   └── *.md                       # 用户手册、API 文档、配置说明等
│   │
│   ├── progress/                      # 进度与路线图
│   │   └── progress-and-roadmap.md    # 已完成里程碑 + 中长期方向
│   │
│   └── verification/                  # 测试策略与验证分析
│       └── *.md                       # 测试框架设计、corner case 分析、测试点等
│
└── .aone_copilot/                     # AI 协作专用（不面向最终用户）
    ├── rules/
    │   ├── workflow.md                # 核心流程：会话恢复、任务分类、完成收尾
    │   └── conventions.md            # 开发约定：规范、文档职责、提交规范
    ├── plans/
    │   └── backlog/TODO.md           # AI 接力清单（跨会话工作记忆）
    └── skills/
        └── <skill-name>/SKILL.md     # 各类任务的执行 skill
```

---

## 各层职责定义

| 层级 | 路径 | 读者 | 核心问题 |
|------|------|------|----------|
| **项目入口** | `README.md` | 所有人 | 这是什么？怎么跑起来？结构是什么样的？ |
| **变更记录** | `CHANGELOG.md` | 所有人 | 这个版本改了什么？ |
| **文档地图** | `docs/README.md` | 所有人 | docs 下有什么？各子目录干什么的？ |
| **架构设计** | `docs/design/` | 开发者 | 系统怎么设计的？为什么这么设计？ |
| **功能 spec** | `docs/specs/` | 开发者 | 某个功能要做什么？不做什么？关键决策是什么？ |
| **使用指南** | `docs/guides/` | 使用者/开发者 | 怎么用？怎么配置？ |
| **进度路线** | `docs/progress/` | 管理者/开发者 | 做完了什么？接下来往哪走？ |
| **验证分析** | `docs/verification/` | 开发者 | 怎么测？哪些 corner case 需要覆盖？ |
| **AI 流程** | `.aone_copilot/rules/` | AI | 恢复上下文读什么？任务怎么分类执行？ |
| **AI 待办** | `.aone_copilot/plans/` | AI | 下一步立刻做什么？ |
| **AI Skill** | `.aone_copilot/skills/` | AI | 某类任务的标准执行流程是什么？ |

---

## 设计原则

1. **面向人 vs 面向 AI 分离**：`docs/` 是人看的，`.aone_copilot/` 是 AI 看的，职责不混
2. **自动生成产物不手编**：如果有脚本生成的文档，在 `docs/README.md` 中标注「自动生成，禁止手编」
3. **docs/README.md 是唯一地图**：进入 `docs/` 目录后看 README 就知道去哪
4. **spec 实现后不删除**：作为设计决策归档，方便回溯 why
5. **TODO 与 progress 互补不重复**：TODO 管「下一步做什么」，progress 管「做完了什么 + 大方向」
6. **skill 带 last-updated**：AI 可判断 skill 是否过时需要更新
7. **子目录按需裁剪**：不是每个项目都需要全部子目录，但已有的子目录必须遵循命名和职责约定

---

## AI 会话恢复标准流程

```
1. 读 .aone_copilot/plans/backlog/TODO.md    → 知道下一步做什么
2. 读 docs/progress/progress-and-roadmap.md  → 知道大背景和已完成什么
3. 读 docs/design/ 下的核心架构文档           → 知道系统怎么设计的
4. 读 README.md                              → 知道项目结构和开发命令
```

---

## 操作规程

### 新增 docs 子目录

执行以下步骤，缺一不可：

1. 在 `docs/` 下创建子目录及其第一个文件
2. **同步 `docs/README.md`**：在文档地图表格中新增一行，写明子目录名、定位、维护方式
3. **同步 `README.md`**：如果项目结构树中展示了 docs 目录，更新树结构
4. **同步 `.aone_copilot/rules/conventions.md`**（如存在）：在文档职责表中追加对应行

### 删除/重命名 docs 子目录

1. 执行实际的目录删除/重命名
2. **同步 `docs/README.md`**：移除或更新对应行
3. **同步 `README.md`**：更新项目结构树和文档导航表
4. **同步 `.aone_copilot/rules/conventions.md`**（如存在）：更新文档职责表
5. **全局搜索旧路径引用**：确认无残留的死链接

### 已有项目对齐审查

1. 读取项目当前 `docs/` 目录结构
2. 与本 skill 的标准结构做 diff
3. 输出差异报告：缺少哪些标准目录、有哪些非标准目录、`docs/README.md` 是否存在且内容完整
4. 提出对齐建议（不强制——允许项目按需裁剪，但命名必须一致）

---

## docs/README.md 模板

新项目初始化时，按以下模板生成 `docs/README.md`（按实际存在的子目录裁剪）：

```markdown
# docs/ 文档目录导航

本目录是 <项目名> 的文档根目录，按用途分为以下子目录：

| 子目录 | 定位 | 维护方式 |
|--------|------|----------|
| [`design/`](./design/) | 架构设计与技术方案 | 模块/接口/数据流变化时手工同步 |
| [`specs/`](./specs/) | 功能设计 spec（实现前的需求分析） | 开发前编写，实现后归档保留 |
| [`guides/`](./guides/) | 使用指南与手册 | 功能/配置变化时同步 |
| [`progress/`](./progress/) | 已完成里程碑 + 中长期路线图 | 完成里程碑级工作后更新 |
| [`verification/`](./verification/) | 测试策略与验证分析 | 测试方案变化时同步 |
```

---

## 与项目级 skill 的关系

本 skill 是**全局通用规范**。如果项目有特化的文档约定（如 RTL-Guard 的 `testpoints/` 是 `verification/` 的特化命名），在项目级 `.aone_copilot/rules/conventions.md` 中记录映射关系：

```markdown
## 本项目文档路径映射（相对通用规范的差异）

| 通用规范路径 | 本项目实际路径 | 原因 |
|-------------|---------------|------|
| `docs/verification/` | `docs/testpoints/` | 本项目验证文档全部是逐规则的 corner case 分析 |
| `docs/guides/` | `docs/guidelines/` | 历史命名，自动生成产物 |
```

这样 AI 在任何项目中都能通过「通用规范 + 项目级映射」定位到正确的文档位置。
