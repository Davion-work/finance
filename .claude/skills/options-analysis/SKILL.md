---
name: options-analysis
description: >
  期权分析 skill。用户提到期权定价、BS模型、Greeks（Delta/Gamma/Theta/Vega/Rho）、隐含波动率(IV)、期权策略（跨式/宽跨式/牛熊价差/蝶式/铁鹰等）、期权链分析、到期损益图时触发。即使用户只说"帮我算一下这个期权值多少"、"IV怎么算"、"这个策略最大亏损多少"，也应使用此 skill。支持A股50ETF期权、沪深300期权、美股期权。
---

# 期权分析 Skill

```bash
pip install numpy scipy pandas matplotlib akshare
```

## Black-Scholes 定价

```python
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

def bs_price(S, K, T, r, sigma, option_type='call'):
    """
    S: 标的现价, K: 行权价, T: 到期时间(年), r: 无风险利率, sigma: 波动率
    """
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    if option_type == 'call':
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    else:
        return K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)
```

## Greeks 计算

```python
def greeks(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    sign = 1 if option_type == 'call' else -1

    delta = sign * norm.cdf(sign * d1)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    theta = (-(S*norm.pdf(d1)*sigma)/(2*np.sqrt(T))
             - sign*r*K*np.exp(-r*T)*norm.cdf(sign*d2)) / 365
    vega  = S * norm.pdf(d1) * np.sqrt(T) / 100   # per 1% vol change
    rho   = sign * K*T*np.exp(-r*T)*norm.cdf(sign*d2) / 100

    return {'delta': delta, 'gamma': gamma, 'theta': theta,
            'vega': vega, 'rho': rho}
```

## 隐含波动率（IV）

```python
def implied_vol(market_price, S, K, T, r, option_type='call'):
    """二分法求解 IV"""
    try:
        iv = brentq(
            lambda sigma: bs_price(S, K, T, r, sigma, option_type) - market_price,
            1e-6, 10.0, xtol=1e-6
        )
        return iv
    except ValueError:
        return np.nan
```

## 常见期权策略

| 策略 | 构成 | 适用场景 |
|------|------|----------|
| 买入跨式 | 买同行权价 call+put | 预期大幅波动，方向不确定 |
| 卖出跨式 | 卖同行权价 call+put | 预期横盘，收取权利金 |
| 牛市价差 | 买低行权价call，卖高行权价call | 温和看涨 |
| 熊市价差 | 买高行权价put，卖低行权价put | 温和看跌 |
| 铁鹰式   | 卖OTM call+put，买更OTM call+put | 区间震荡，有限风险 |
| 蝶式     | 买1个低+买1个高，卖2个中间行权价 | 预期到期价格接近中间行权价 |

```python
def strategy_payoff(S_range, legs):
    """
    legs: list of (option_type, position, K, premium)
    position: +1 买入, -1 卖出
    """
    payoff = np.zeros_like(S_range, dtype=float)
    for opt_type, pos, K, premium in legs:
        if opt_type == 'call':
            payoff += pos * (np.maximum(S_range - K, 0) - premium)
        else:
            payoff += pos * (np.maximum(K - S_range, 0) - premium)
    return payoff
```

## A股期权数据（AkShare）

```python
import akshare as ak

# 50ETF期权合约列表
df = ak.option_current_em(symbol="上证50ETF")

# 期权链（某一到期日）
chain = ak.option_finance_board(symbol="510050", date="2025-03")

# 实时行情
quote = ak.option_value_analysis_em()
```

## 到期损益图

```python
import matplotlib.pyplot as plt

S_range = np.linspace(S*0.7, S*1.3, 300)
legs = [('call', +1, K1, p1), ('call', -1, K2, p2)]
pnl = strategy_payoff(S_range, legs)

plt.figure(figsize=(10, 5))
plt.plot(S_range, pnl)
plt.axhline(0, color='k', linewidth=0.8)
plt.axvline(S, color='r', linestyle='--', label='当前价格')
plt.fill_between(S_range, pnl, 0, where=(pnl>0), alpha=0.3, color='green')
plt.fill_between(S_range, pnl, 0, where=(pnl<0), alpha=0.3, color='red')
plt.xlabel('到期日标的价格')
plt.ylabel('盈亏')
plt.title('期权策略到期损益图')
plt.legend()
plt.savefig('option_payoff.png', dpi=150)
```

## 分析报告结构

```
# 期权分析报告：[标的] [策略名]
## 市场参数（S/K/T/r/sigma）
## 定价结果（理论价格 vs 市场价格）
## Greeks 汇总表
## 隐含波动率 & 历史波动率对比
## 策略损益分析（最大盈利/最大亏损/盈亏平衡点）
## 风险提示
```

## 关键提醒

- T 单位为**年**：距到期N天 → `T = N/365`
- 国内无风险利率参考1年期LPR或国债收益率（约2.0%~2.5%）
- IV > HV 通常意味期权偏贵，反之偏便宜
- Delta 对冲需考虑 Gamma 风险（大幅波动时 Delta 变化快）
