# 📈 期权分析工具箱 Options Analysis Toolkit

纯前端期权（Options）交互式分析工具套件，基于 **Black-Scholes 模型**，涵盖从入门学习到实战操作的全流程。无需后端，双击 HTML 即可使用。

## 功能模块总览

本工具箱共包含 **9 个功能页面**，通过顶部 Tab 导航互相跳转：

| # | 页面文件 | 功能名称 | 一句话描述 |
|---|----------|----------|------------|
| 1 | `options-payoff.html` | 单腿策略损益 | Buy/Sell Call/Put 四种基础头寸的到期损益图 |
| 2 | `options-strategy.html` | 组合策略损益 | 6 种经典组合策略的损益图 + 详细文档 |
| 3 | `options-advanced.html` | 进阶策略 | PMCC、Calendar、Diagonal、Jade Lizard、Ratio 等高级策略 |
| 4 | `options-probability.html` | 概率计算器 | POP（盈利概率）、Expected Move、概率分布可视化 |
| 5 | `options-quotes.html` | 实时行情 | Live Option Chain 期权链行情展示 |
| 6 | `options-guide.html` | 策略指南 | 按场景索引策略选择，含实现逻辑说明 |
| 7 | `options-playbook.html` | 场景 Playbook | 操作手册，实战场景下的具体操作步骤 |
| 8 | `options-adjustments.html` | 调整决策树 | 持仓不利时的调整方案决策树 |
| 9 | `options-glossary.html` | 术语词典 | Greeks、BS 模型、波动率、策略术语的完整释义 |

---

## 详细功能介绍

### 1. 单腿策略损益分析 (`options-payoff.html`)

四种基础期权头寸的实时损益可视化。

**支持策略：**
| 策略 | 说明 | 盈亏特征 |
|------|------|----------|
| 买入看涨 Long Call | 看涨 | 亏损有限，盈利无限 |
| 卖出看涨 Short Call | 中性偏空 | 盈利有限，亏损无限 |
| 买入看跌 Long Put | 看跌 | 亏损有限，盈利有限 |
| 卖出看跌 Short Put | 中性偏多 | 盈利有限，亏损有限 |

**功能特性：**
- 两种视图模式：到期损益 / 当前估值（含时间价值）
- 5 个可调参数：现价 S、行权价 K、到期天数 T、波动率 σ、无风险利率 r
- 实时 Greeks 展示：Delta (Δ)、Gamma (Γ)、Theta (Θ)、Vega (ν)
- 策略摘要卡片：权利金、盈亏平衡点、最大盈利/亏损

### 2. 组合策略损益分析 (`options-strategy.html`)

六种市场最常用的经典组合策略，含交互式损益图和完整文档。

**支持策略：**
| 策略 | 英文名 | 适用场景 |
|------|--------|----------|
| 牛市看涨价差 | Bull Call Spread | 温和看涨 |
| 熊市看跌价差 | Bear Put Spread | 温和看跌 |
| 买入跨式 | Long Straddle | 预期大幅波动 |
| 卖出跨式 | Short Straddle | 预期横盘 |
| 铁鹰式 | Iron Condor | 区间震荡，有限风险 |
| 蝶式价差 | Butterfly Spread | 精确预测到期价 |

**功能特性：**
- 每种策略可独立调节各腿行权价
- 组合盈亏曲线 + 各单腿虚线辅助对比
- 右侧文档面板：策略概述、构成方式、盈亏公式、情境分析、适用场景、风险提示
- 底部统计卡片：最大盈利/亏损、盈亏平衡点、净权利金、策略构成

### 3. 进阶策略 (`options-advanced.html`)

面向有经验的交易者，5 种进阶组合策略的构成、盈亏图、Greeks 特征及适用场景详解。

**支持策略：**
- **PMCC**（Poor Man's Covered Call）— 用 LEAPS 替代持股的备兑策略，降低资金占用
- **Calendar Spread**（日历价差）— 利用不同到期日的时间衰减差异获利
- **Diagonal Spread**（对角价差）— 同时跨行权价和到期日，兼具方向性和时间价值
- **Jade Lizard** — 卖出看跌 + 卖出看涨价差，构造零上行风险的收入策略
- **Ratio Spread**（比率价差）— 不等量买卖的非对称策略，适合特定波动率环境

### 4. 概率计算器 (`options-probability.html`)

基于 BS 模型的概率分析工具。

**核心功能：**
- **POP**（Probability of Profit）— 策略到期盈利的概率
- **Expected Move** — 基于隐含波动率的预期波动范围
- **概率分布图** — 可视化到期价格的对数正态分布
- 支持自定义价格区间的概率计算

### 5. 实时行情 (`options-quotes.html`)

期权链（Option Chain）行情展示界面，支持输入股票代码查询实时期权链数据。

**核心功能：**
- 按到期日分组的期权链展示
- Call/Put 对称布局
- 实值/虚值/平值高亮
- 关键指标：买卖价、成交量、未平仓量、IV、Greeks

**⚠️ 依赖说明：** 本页面需要配合本地 Python 后端服务运行（`localhost:5000`），通过 Yahoo Finance 获取实时数据。需要科学上网环境访问 Yahoo Finance，或可替换为 AKShare 获取 A 股 50ETF/300ETF 期权数据。

### 6. 策略指南 (`options-guide.html`)

按 12 种市场场景索引 10 种策略，提供从场景到策略的快速决策路径。

**核心功能：**
- 上半部分：12 种常见市场场景（强烈看涨、温和看涨、温和看跌、强烈看跌等），每种场景给出首选/次选/应避免的策略推荐及优缺权衡
- 下半部分：10 种策略的详细实现逻辑卡片，含构成方式、Greeks 特征、适用场景

### 7. 场景 Playbook (`options-playbook.html`)

实战操作手册，提供具体场景下的完整操作流程。

**核心功能：**
- 常见交易场景的 Step-by-Step 操作指引
- 入场条件、仓位管理、出场规则
- 实际案例分析
- 风险管理检查清单

### 8. 调整决策树 (`options-adjustments.html`)

持仓不利时的系统化调整方案。

**核心功能：**
- 交互式决策树：根据当前持仓状态选择调整方案
- 常见调整手法：Roll Up/Down/Out、转换策略、加腿保护
- 每种调整的成本/收益分析
- 何时止损 vs 何时调整的判断框架

### 9. 术语词典 (`options-glossary.html`)

期权相关术语的完整参考词典。

**覆盖范围：**
- **Greeks**：Delta、Gamma、Theta、Vega、Rho 及高阶 Greeks
- **BS 模型**：公式推导、假设条件、局限性
- **波动率**：历史波动率 HV、隐含波动率 IV、波动率微笑/偏斜
- **策略术语**：ITM/ATM/OTM、内在价值/时间价值、行权/指派等
- **市场术语**：Pin Risk、Gamma Squeeze、Vol Crush 等

---

## 技术栈

- **纯前端**：无后端依赖，双击 HTML 即可使用
- **Chart.js 4.4.0**：图表渲染
- **chartjs-plugin-annotation 3.0.1**：辅助参考线
- **Black-Scholes 模型**：期权理论定价（含 erf 近似实现）
- **深色主题 UI**：GitHub Dark 风格，统一视觉体验

## 使用方式

```bash
# 直接在浏览器中打开任意页面
open options-payoff.html
```

所有页面通过顶部 Tab 导航栏互相跳转，无需记忆文件名。

## 核心算法

### Black-Scholes 定价公式

```
Call = S·Φ(d₁) − K·e^(−rT)·Φ(d₂)
Put  = K·e^(−rT)·Φ(−d₂) − S·Φ(−d₁)

d₁ = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
d₂ = d₁ − σ·√T
```

### 默认参数

| 参数 | 符号 | 默认值 | 范围 |
|------|------|--------|------|
| 标的现价 | S | 100 | 10 ~ 500 |
| 行权价 | K | 100 | 10 ~ 500 |
| 到期天数 | T | 30 天 | 1 ~ 365 |
| 波动率 | σ | 25% | 5% ~ 150% |
| 无风险利率 | r | 2.5% | 0% ~ 15% |

## 项目结构

```
options-learning-analysis/
├── options-payoff.html        # 单腿策略损益分析
├── options-strategy.html      # 组合策略损益分析
├── options-advanced.html      # 进阶策略分析
├── options-probability.html   # 概率计算器
├── options-quotes.html        # 实时行情 Option Chain
├── options-guide.html         # 策略指南（场景索引）
├── options-playbook.html      # 场景 Playbook（操作手册）
├── options-adjustments.html   # 调整决策树
├── options-glossary.html      # 术语词典
├── quotes_server.py           # Yahoo Finance 代理服务
├── README.md                  # 本文件
└── docs/                      # 项目文档
    ├── README.md              # 文档目录导航
    └── progress/
        └── progress-and-roadmap.md  # 未来增补计划
```

## License

MIT
