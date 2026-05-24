# 期权机会分析发现 (Options Opportunity Discovery)

美股期权机会自动发现与分析工具。通过读取市场期权数据，自动筛选出适合投资的期权标的。

## 功能模块

### 1. 数据获取层
- 数据源：Yahoo Finance
- 获取美股期权链数据（标的价格、期权链、Greeks 等）
- 初期：手动触发 / 每日更新；后续提高频率

### 2. 策略分析层

#### LEAPS Call 策略
筛选适合买入远期看涨期权的标的：
- 筛选条件：流动性、隐含波动率、Delta 范围、到期时间等

#### Sell Put 策略
筛选适合卖出看跌期权的标的：
- 筛选条件：年化收益率、安全边际、隐含波动率百分位等

## 技术架构

- **后端**：Python (Flask) — 数据获取与策略计算
- **前端**：HTML + JavaScript — 结果展示与交互
- **数据源**：Yahoo Finance API (yfinance)

## 快速开始

```bash
pip install -r requirements.txt
python server.py
```

浏览器打开 http://localhost:5000
