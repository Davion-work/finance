"""Sell Put 策略分析模块

筛选适合卖出看跌期权的标的。
核心逻辑：卖出 OTM Put，收取权利金，愿意在更低价格接盘。

筛选逻辑：
- 年化收益率达到目标阈值
- 行权价提供足够安全边际（OTM 程度）
- 合约有足够流动性
- 标的本身是愿意持有的优质股票
"""

import pandas as pd
from datetime import datetime


class SellPutStrategy:
    """Sell Put 策略筛选器"""

    def __init__(
        self,
        min_annualized_return: float = 0.10,
        min_otm_percentage: float = 0.05,
        max_otm_percentage: float = 0.30,
        min_days_to_expiry: int = 20,
        max_days_to_expiry: int = 60,
        min_open_interest: int = 50,
    ):
        self.min_annualized_return = min_annualized_return
        self.min_otm_percentage = min_otm_percentage
        self.max_otm_percentage = max_otm_percentage
        self.min_days_to_expiry = min_days_to_expiry
        self.max_days_to_expiry = max_days_to_expiry
        self.min_open_interest = min_open_interest

    def analyze(self, option_data: dict) -> list[dict]:
        """分析单个标的的 Sell Put 机会

        Args:
            option_data: 期权数据，puts 字段支持 DataFrame 或 list[dict] 格式

        Returns:
            符合条件的期权合约列表
        """
        puts = option_data.get("puts")
        if puts is None:
            return []

        # 兼容 DataFrame 和 list[dict] 两种格式
        if isinstance(puts, pd.DataFrame):
            if puts.empty:
                return []
            puts_records = puts.to_dict(orient="records")
        elif isinstance(puts, list):
            if not puts:
                return []
            puts_records = puts
        else:
            return []

        current_price = option_data.get("currentPrice")
        if not current_price or current_price <= 0:
            return []

        ticker = option_data["ticker"]
        today = datetime.now()

        opportunities = []

        for row in puts_records:
            exp_date = pd.to_datetime(row.get("expirationDate"))
            days_to_expiry = (exp_date - today).days

            if not (self.min_days_to_expiry <= days_to_expiry <= self.max_days_to_expiry):
                continue

            strike = row.get("strike", 0)
            bid = row.get("bid", 0) or 0
            open_interest = row.get("openInterest", 0) or 0

            if open_interest < self.min_open_interest:
                continue

            if bid <= 0:
                continue

            # 计算 OTM 程度（安全边际）
            otm_percentage = (current_price - strike) / current_price if current_price > 0 else 0

            if not (self.min_otm_percentage <= otm_percentage <= self.max_otm_percentage):
                continue

            # 计算年化收益率（基于保证金 = 行权价）
            premium_return = bid / strike if strike > 0 else 0
            annualized_return = premium_return * (365 / days_to_expiry) if days_to_expiry > 0 else 0

            if annualized_return < self.min_annualized_return:
                continue

            implied_vol = row.get("impliedVolatility", 0) or 0

            opportunities.append({
                "ticker": ticker,
                "strike": strike,
                "expirationDate": row.get("expirationDate"),
                "daysToExpiry": days_to_expiry,
                "bid": bid,
                "ask": row.get("ask", 0),
                "impliedVolatility": implied_vol,
                "openInterest": open_interest,
                "volume": row.get("volume", 0) or 0,
                "otmPercentage": round(otm_percentage * 100, 2),
                "annualizedReturn": round(annualized_return * 100, 2),
                "maxLoss": round(strike - bid, 2),
                "currentPrice": current_price,
            })

        # 按年化收益率排序
        opportunities.sort(key=lambda x: x["annualizedReturn"], reverse=True)
        return opportunities
