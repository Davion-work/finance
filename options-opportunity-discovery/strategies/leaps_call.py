"""LEAPS Call 策略分析模块

筛选适合买入远期看涨期权的标的。
LEAPS = Long-Term Equity Anticipation Securities，到期日通常 > 1 年。

筛选逻辑：
- 到期时间 >= 180 天（偏向 1 年以上）
- 通过 BSM 模型计算 Delta，筛选 Delta 在目标范围内的合约
- 合约有足够流动性（open interest / volume）
- 隐含波动率不超过阈值（避免 IV 过高导致期权过贵）
"""

import math
import pandas as pd
from datetime import datetime
from scipy.stats import norm


def calculate_bsm_delta(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    implied_vol: float,
) -> float:
    """使用 Black-Scholes-Merton 模型计算 Call Delta

    Args:
        spot: 标的当前价格
        strike: 行权价
        time_to_expiry_years: 距到期的年数
        risk_free_rate: 无风险利率
        implied_vol: 隐含波动率

    Returns:
        Call Delta 值 (0~1)
    """
    if spot <= 0 or strike <= 0 or time_to_expiry_years <= 0 or implied_vol <= 0:
        return 0.0

    d1 = (
        math.log(spot / strike)
        + (risk_free_rate + 0.5 * implied_vol ** 2) * time_to_expiry_years
    ) / (implied_vol * math.sqrt(time_to_expiry_years))

    return norm.cdf(d1)


class LeapsCallStrategy:
    """LEAPS Call 策略筛选器"""

    def __init__(
        self,
        min_days_to_expiry: int = 180,
        delta_range: tuple[float, float] = (0.50, 0.80),
        min_open_interest: int = 100,
        max_implied_volatility: float = 0.80,
        risk_free_rate: float = 0.045,
    ):
        self.min_days_to_expiry = min_days_to_expiry
        self.delta_range = delta_range
        self.min_open_interest = min_open_interest
        self.max_implied_volatility = max_implied_volatility
        self.risk_free_rate = risk_free_rate

    def analyze(self, option_data: dict) -> list[dict]:
        """分析单个标的的 LEAPS Call 机会

        Args:
            option_data: 期权数据，calls 字段支持 DataFrame 或 list[dict] 格式

        Returns:
            符合条件的期权合约列表
        """
        calls = option_data.get("calls")
        if calls is None:
            return []

        # 兼容 DataFrame 和 list[dict] 两种格式（缓存为 list[dict]）
        if isinstance(calls, pd.DataFrame):
            if calls.empty:
                return []
            calls_records = calls.to_dict(orient="records")
        elif isinstance(calls, list):
            if not calls:
                return []
            calls_records = calls
        else:
            return []

        current_price = option_data.get("currentPrice")
        if not current_price or current_price <= 0:
            return []

        ticker = option_data["ticker"]
        today = datetime.now()

        opportunities = []

        for row in calls_records:
            exp_date = pd.to_datetime(row.get("expirationDate"))
            days_to_expiry = (exp_date - today).days

            if days_to_expiry < self.min_days_to_expiry:
                continue

            open_interest = row.get("openInterest", 0) or 0
            if open_interest < self.min_open_interest:
                continue

            implied_vol = row.get("impliedVolatility", 0) or 0
            if implied_vol <= 0 or implied_vol > self.max_implied_volatility:
                continue

            strike = row.get("strike", 0)
            last_price = row.get("lastPrice", 0) or 0

            if strike <= 0 or last_price <= 0:
                continue

            # 使用 BSM 计算真实 Delta
            time_to_expiry_years = days_to_expiry / 365.0
            delta = calculate_bsm_delta(
                spot=current_price,
                strike=strike,
                time_to_expiry_years=time_to_expiry_years,
                risk_free_rate=self.risk_free_rate,
                implied_vol=implied_vol,
            )

            if not (self.delta_range[0] <= delta <= self.delta_range[1]):
                continue

            # 计算杠杆倍数和盈亏平衡点
            leverage = current_price / last_price
            breakeven = strike + last_price

            opportunities.append({
                "ticker": ticker,
                "strike": strike,
                "expirationDate": row.get("expirationDate"),
                "daysToExpiry": days_to_expiry,
                "lastPrice": last_price,
                "bid": row.get("bid", 0),
                "ask": row.get("ask", 0),
                "delta": round(delta, 3),
                "impliedVolatility": implied_vol,
                "openInterest": open_interest,
                "volume": row.get("volume", 0) or 0,
                "leverage": round(leverage, 2),
                "breakeven": round(breakeven, 2),
                "currentPrice": current_price,
            })

        # 按杠杆倍数排序
        opportunities.sort(key=lambda x: x["leverage"], reverse=True)
        return opportunities
