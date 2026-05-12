---
name: stock-analysis
description: >
  A股/港股/美股行情分析 skill。当用户需要获取股票数据、分析K线走势、计算技术指标（均线/MACD/RSI/布林带）、分析成交量、查询个股或板块行情、做股票比较分析、或生成行情分析报告时触发此 skill。支持 AkShare（免费）和 Tushare（需token）数据源。即使用户只是说"帮我看看这只股票"、"分析一下行情"、"最近走势怎么样"，也应该使用此 skill。
---

# 股票行情分析 Skill

## 数据源选择

优先使用 **AkShare**（无需注册，免费），备选 **Tushare**（需要 token）。

```bash
pip install akshare tushare pandas matplotlib mplfinance
```

## 数据获取

### A股
```python
import akshare as ak

# 日K数据（股票代码如 "000001" 平安银行）
df = ak.stock_zh_a_hist(symbol="000001", period="daily",
                         start_date="20240101", end_date="20241231",
                         adjust="qfq")  # qfq=前复权, hfq=后复权, ""=不复权

# 实时行情
df_rt = ak.stock_zh_a_spot_em()

# 个股基本面
info = ak.stock_individual_info_em(symbol="000001")
```

### 港股
```python
df = ak.stock_hk_hist(symbol="00700", period="daily",
                       start_date="20240101", end_date="20241231", adjust="qfq")
```

### 美股
```python
df = ak.stock_us_hist(symbol="AAPL", period="daily",
                       start_date="20240101", end_date="20241231", adjust="qfq")
```

## 技术指标计算

```python
import pandas as pd

def add_indicators(df):
    # 均线
    df['MA5']  = df['收盘'].rolling(5).mean()
    df['MA10'] = df['收盘'].rolling(10).mean()
    df['MA20'] = df['收盘'].rolling(20).mean()
    df['MA60'] = df['收盘'].rolling(60).mean()

    # MACD
    ema12 = df['收盘'].ewm(span=12).mean()
    ema26 = df['收盘'].ewm(span=26).mean()
    df['DIF'] = ema12 - ema26
    df['DEA'] = df['DIF'].ewm(span=9).mean()
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])

    # RSI (14日)
    delta = df['收盘'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    df['RSI14'] = 100 - 100 / (1 + gain / loss)

    # 布林带 (20日)
    df['BB_mid']   = df['收盘'].rolling(20).mean()
    df['BB_upper'] = df['BB_mid'] + 2 * df['收盘'].rolling(20).std()
    df['BB_lower'] = df['BB_mid'] - 2 * df['收盘'].rolling(20).std()

    return df
```

## K线图绘制

```python
import mplfinance as mpf

# 准备 mplfinance 格式（列名需为 Open/High/Low/Close/Volume）
df_plot = df.rename(columns={
    '开盘': 'Open', '最高': 'High', '最低': 'Low',
    '收盘': 'Close', '成交量': 'Volume'
})
df_plot.index = pd.to_datetime(df_plot['日期'])

mpf.plot(df_plot, type='candle', style='charles',
         volume=True, mav=(5, 20, 60),
         title='股票K线图', savefig='kline.png')
```

## 分析报告结构

生成报告时，按以下结构组织：

```
# [股票名称]([代码]) 行情分析报告
## 基本信息
## 近期走势摘要（涨跌幅、振幅、成交量变化）
## 技术指标分析（均线、MACD、RSI、布林带）
## 支撑位与阻力位
## 综合判断
```

## 注意事项

- A股交易日为周一至周五，节假日休市
- 复权处理：长期分析用前复权(qfq)，短期不复权
- AkShare 接口可能限速，批量请求时加 `time.sleep(0.5)`
- 美股列名为英文（Open/High/Low/Close/Volume），港股/A股为中文
