---
name: smart-web-search
description: >
  【MCP配置读取】本技能运行时必须先读取同目录下的 mcp-config.json 文件获取 MCP 服务 URL，
  然后使用这些 URL 调用 MCP 服务。严禁在未读取 mcp-config.json 的情况下直接调用 MCP。

  智能全网搜索助手。当用户需要搜索信息、调研话题、查找最新资讯、做竞品分析、
  了解某个概念或事件时使用。支持博查+小宿双引擎联合搜索，结合秘塔AI对
  重要链接进行全文精读，输出结构化调研报告。
  每当用户说「搜索」「查一下」「帮我了解」「调研」「查资料」「最新动态」时应使用本技能。
metadata:
  label: 智能全网搜索
---

# 智能全网搜索

专业的全网信息检索与分析助手。调用 3 个 MCP 搜索/速读工具，快速获取多源信息并整合为结构化调研报告。

## MCP 服务配置

本技能依赖以下 MCP 服务，运行时**必须**先读取 `mcp-config.json` 获取服务 URL：

| 环境变量名 | MCP 服务 | mcpId | 用途 |
|-----------|----------|-------|------|
| `$MCP_BOCHA_URL` | 博查搜索 | 1039 | 全网深度搜索，支持时效过滤 |
| `$MCP_XIAOSU_URL` | 小宿智能搜索 | 6440 | 中文语义搜索，站内优质内容 |
| `$MCP_READER_URL` | 秘塔AI-链接速读 | 9400 | 对 URL 进行全文精读提取 |

### 配置读取方式

**约束：调用方 agent 必须在执行任何 MCP 调用前，先读取 mcp-config.json 文件**

```python
import json

with open("mcp-config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bocha_url = config["MCP_BOCHA_URL"]["url"]
xiaosu_url = config["MCP_XIAOSU_URL"]["url"]
reader_url = config["MCP_READER_URL"]["url"]
```

## 工作流程

### 第一步：理解搜索意图

收到用户请求后，判断搜索类型：
- **快速查询**：事实性问题 → 单引擎搜索即可
- **深度调研**：话题/竞品/趋势 → 双引擎联合搜索 + 链接精读

### 第二步：多引擎联合搜索

1. **读取配置**：首先读取 `mcp-config.json` 获取所有 MCP 服务的 URL
2. **验证配置**：检查所需服务的 URL 是否已配置
3. **执行搜索**：

```bash
# 1. 博查搜索 — 全网广度覆盖
python3 scripts/call_mcp.py call "$MCP_BOCHA_URL" web_search \
  --params '{"query": "<用户查询>", "count": 10, "freshness": "noLimit", "summary": true}'

# 2. 小宿智能搜索 — 中文语义补充（工具名自动发现）
python3 scripts/call_mcp.py list "$MCP_XIAOSU_URL"
python3 scripts/call_mcp.py call "$MCP_XIAOSU_URL" <发现的工具名> \
  --params '{"query": "<用户查询>"}'
```

freshness 参数可选值：`oneDay` | `oneWeek` | `oneMonth` | `oneYear` | `noLimit`

### 第三步：链接精读（按需）

对搜索结果中最相关的 2-3 个链接，使用秘塔AI全文精读：

```bash
python3 scripts/call_mcp.py list "$MCP_READER_URL"
python3 scripts/call_mcp.py call "$MCP_READER_URL" <发现的工具名> \
  --params '{"url": "<目标链接>"}'
```

### 第四步：整合输出报告

将所有搜索结果和精读内容整合为结构化报告。

## 输出格式

### 快速查询模式

```
## 搜索结果：<查询关键词>

### 核心答案
<直接回答用户问题>

### 相关来源
1. [标题](链接) — 摘要
2. [标题](链接) — 摘要
```

### 深度调研模式

```
## 调研报告：<主题>

### 摘要
<100字以内的核心发现>

### 详细发现
#### 1. <发现维度一>
<内容，引用来源>

#### 2. <发现维度二>
<内容，引用来源>

### 精读摘要
- [文章标题](链接)：<全文要点提取>

### 数据来源
- 博查搜索：X 条结果
- 小宿搜索：X 条结果
- 秘塔精读：X 篇全文
```

## 注意事项

- 搜索引擎返回结果后，去重合并，按相关性排序
- 优先展示有明确来源的信息
- 对矛盾信息标注不同来源的说法
- 精读仅用于高价值链接，避免无意义消耗
- 如果某个引擎调用失败，用剩余引擎继续完成任务，不中断流程
