---
name: quant-backtest
description: >
  量化策略回测 skill。用户提到策略回测、backtesting、vectorbt、backtrader、因子选股、技术指标策略、绩效评估（夏普/最大回撤/胜率/Calmar）、参数优化、信号生成时触发。即使用户说"帮我测试一下这个策略历史表现"、"这个方法回测一下"、"看看均线策略效果怎样"，也应使用此 skill。
---

# 量化回测 Skill

```bash
pip install vectorbt backtrader akshare pandas numpy matplotlib
```

## 框架选择

| 框架 | 适合场景 | 速度 |
|------|---------|------|
| **vectorbt** | 快速原型、参数扫描、向量化计算 | 极快 |
| **backtrader** | 复杂逻辑、事件驱动、多资产 | 中等 |
| 纯 pandas | 简单策略、教学演示 | 快 |

## vectorbt 回测（推荐快速验证）

```python
import vectorbt as vbt
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_zh_a_hist(symbol="000001", period="daily",
                         start_date="20200101", end_date="20241231", adjust="qfq")
df.index = pd.to_datetime(df['日期'])
close = df['收盘']

# 双均线策略
fast_ma = vbt.MA.run(close, window=10)
slow_ma = vbt.MA.run(close, window=30)

entries = fast_ma.ma_crossed_above(slow_ma)
exits   = fast_ma.ma_crossed_below(slow_ma)

pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=100000, fees=0.001)
print(pf.stats())
pf.plot().show()
```

## 参数网格扫描

```python
fast_windows = range(5, 30, 5)
slow_windows = range(20, 100, 10)

fast_ma = vbt.MA.run(close, window=fast_windows, short_name='fast')
slow_ma = vbt.MA.run(close, window=slow_windows, short_name='slow')

entries = fast_ma.ma_crossed_above(slow_ma)
exits   = fast_ma.ma_crossed_below(slow_ma)

pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=100000, fees=0.001)

# 热力图：夏普比率
pf.sharpe_ratio().vbt.heatmap(
    x_level='fast_window', y_level='slow_window'
).show()
```

## backtrader 回测（复杂逻辑）

```python
import backtrader as bt

class MACrossStrategy(bt.Strategy):
    params = (('fast', 10), ('slow', 30),)

    def __init__(self):
        self.fast_ma = bt.ind.SMA(period=self.p.fast)
        self.slow_ma = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.sell()

cerebro = bt.Cerebro()
cerebro.addstrategy(MACrossStrategy)
cerebro.broker.setcash(100000)
cerebro.broker.setcommission(0.001)

data = bt.feeds.PandasData(dataname=df_ohlcv)
cerebro.adddata(data)
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

results = cerebro.run()
strat = results[0]
print('夏普比率:', strat.analyzers.sharpe.get_analysis())
print('最大回撤:', strat.analyzers.drawdown.get_analysis())
cerebro.plot()
```

## 绩效指标计算

```python
import numpy as np

def performance_metrics(returns, risk_free=0.02):
    """returns: 日收益率序列（Series）"""
    ann_ret  = (1 + returns).prod() ** (252/len(returns)) - 1
    ann_vol  = returns.std() * np.sqrt(252)
    sharpe   = (ann_ret - risk_free) / ann_vol

    cumulative  = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown    = (cumulative - rolling_max) / rolling_max
    max_dd      = drawdown.min()

    calmar       = ann_ret / abs(max_dd)
    win_rate     = (returns > 0).mean()
    profit_factor = returns[returns>0].sum() / abs(returns[returns<0].sum())

    return {
        '年化收益率': f'{ann_ret:.2%}',
        '年化波动率': f'{ann_vol:.2%}',
        '夏普比率':   f'{sharpe:.2f}',
        '最大回撤':   f'{max_dd:.2%}',
        'Calmar比率': f'{calmar:.2f}',
        '胜率':       f'{win_rate:.2%}',
        '盈亏比':     f'{profit_factor:.2f}',
    }
```

## 常见坑

- **未来函数**：信号只用 `t` 时刻之前数据，`shift(1)` 确保次日执行
- **手续费**：A股双边 0.1%~0.3%，含印花税（卖出 0.1%）
- **滑点**：`fees=0.002` 粗略覆盖高频场景
- **过拟合**：参数扫描后必须用样本外数据验证（walk-forward）
- **生存偏差**：历史成分股会变，用当时成分股数据

## 回测报告结构

```
# 策略回测报告：[策略名]
## 策略逻辑说明
## 参数设置
## 回测区间 & 数据说明
## 净值曲线图
## 绩效指标汇总（夏普/回撤/胜率/盈亏比/Calmar）
## 与基准对比（沪深300/标普500）
## 参数敏感性分析
## 结论与风险
```
