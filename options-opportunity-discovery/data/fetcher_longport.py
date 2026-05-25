"""期权数据获取模块 - 长桥 OpenAPI 数据源

从长桥获取美股期权链数据，输出格式与 yfinance 版本完全一致，
策略层无需感知数据源差异。

依赖：
- longport SDK
- python-dotenv（加载 .longbridgeapi 配置文件）
"""

import math
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from longport.openapi import QuoteContext, Config
from scipy.stats import norm

from data.cache import is_cache_fresh, save_to_cache, load_from_cache

# 加载长桥凭证
_PROJECT_DIR = Path(__file__).resolve().parent.parent
_CREDENTIAL_FILE = _PROJECT_DIR / ".longbridgeapi"
load_dotenv(_CREDENTIAL_FILE)

# 无风险利率（用于 BSM Delta 计算）
RISK_FREE_RATE = 0.045


def _to_longport_symbol(ticker: str) -> str:
    """内部 ticker（如 NVDA）转长桥格式（NVDA.US）"""
    ticker = ticker.upper().strip()
    if not ticker.endswith(".US"):
        return f"{ticker}.US"
    return ticker


def _from_longport_symbol(symbol: str) -> str:
    """长桥格式（NVDA.US）转内部 ticker（NVDA）"""
    if symbol.endswith(".US"):
        return symbol[:-3]
    return symbol


def _calculate_delta(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    implied_vol: float,
    is_call: bool,
) -> float:
    """BSM Delta 计算"""
    if spot <= 0 or strike <= 0 or time_to_expiry_years <= 0 or implied_vol <= 0:
        return 0.0

    d1 = (
        math.log(spot / strike)
        + (RISK_FREE_RATE + 0.5 * implied_vol ** 2) * time_to_expiry_years
    ) / (implied_vol * math.sqrt(time_to_expiry_years))

    if is_call:
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1.0


def _days_to_expiry(expiry_date: date) -> int:
    """计算距到期日的天数"""
    today = date.today()
    return (expiry_date - today).days


class LongportOptionDataFetcher:
    """从长桥 OpenAPI 获取期权数据，输出格式与 yfinance 版本一致"""

    def __init__(
        self,
        request_interval: float = 0.5,
        batch_pause: float = 3.0,
        batch_size: int = 10,
        max_retries: int = 3,
    ):
        self.request_interval = request_interval
        self.batch_pause = batch_pause
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._ctx: Optional[QuoteContext] = None

    def _get_context(self) -> QuoteContext:
        """懒初始化长桥 QuoteContext"""
        if self._ctx is None:
            config = Config.from_env()
            self._ctx = QuoteContext(config)
        return self._ctx

    def fetch_option_chain(self, ticker: str) -> Optional[dict]:
        """获取指定标的的完整期权链数据

        Args:
            ticker: 股票代码（如 'NVDA'，无需 .US 后缀）

        Returns:
            与 yfinance 版本格式一致的字典，失败返回 None
        """
        longport_symbol = _to_longport_symbol(ticker)

        for attempt in range(self.max_retries):
            try:
                ctx = self._get_context()

                # 获取标的现价
                quotes = ctx.quote([longport_symbol])
                if not quotes:
                    print(f"[ERROR] {ticker}: No quote data")
                    return None
                current_price = float(quotes[0].last_done)
                if current_price <= 0:
                    return None

                # 获取到期日列表
                expiry_dates = ctx.option_chain_expiry_date_list(longport_symbol)
                if not expiry_dates:
                    print(f"[ERROR] {ticker}: No expiry dates")
                    return None

                all_calls = []
                all_puts = []

                # 只获取策略关心的到期日范围
                # Sell Put: 14-60天（当前主要策略）
                # LEAPS Call: 180-730天（暂不启用，节省请求量）
                MIN_DAYS = 14
                MAX_DAYS = 60
                valid_expiries = [d for d in expiry_dates
                                  if MIN_DAYS <= _days_to_expiry(d) <= MAX_DAYS]

                for expiry in valid_expiries:
                    days_left = _days_to_expiry(expiry)

                    time_to_expiry_years = days_left / 365.0
                    exp_date_str = str(expiry)

                    # 获取该到期日的行权价列表
                    chain_info = ctx.option_chain_info_by_date(longport_symbol, expiry)
                    if not chain_info:
                        continue

                    # 收集 ATM 附近的 call/put symbol（上下各15个行权价）
                    # 避免请求过多触发频率限制
                    sorted_chain = sorted(chain_info, key=lambda x: abs(float(x.price) - current_price))
                    nearby_chain = sorted_chain[:15]

                    call_symbols = []
                    put_symbols = []

                    for item in nearby_chain:
                        if item.call_symbol:
                            call_symbols.append(item.call_symbol)
                        if item.put_symbol:
                            put_symbols.append(item.put_symbol)

                    # 批量获取期权报价
                    call_quotes = self._batch_option_quote(call_symbols)
                    put_quotes = self._batch_option_quote(put_symbols)

                    # 转换为标准格式
                    for oq in call_quotes:
                        strike = float(oq.strike_price)
                        iv = float(oq.implied_volatility) if oq.implied_volatility else 0.0
                        delta = _calculate_delta(current_price, strike, time_to_expiry_years, iv, True)
                        in_the_money = current_price > strike

                        all_calls.append({
                            "strike": strike,
                            "lastPrice": float(oq.last_done),
                            "bid": float(oq.last_done) * 0.95,  # 估算 bid（长桥L1无bid/ask）
                            "ask": float(oq.last_done) * 1.05,  # 估算 ask
                            "volume": int(oq.volume) if oq.volume else 0,
                            "openInterest": int(oq.open_interest) if oq.open_interest else 0,
                            "impliedVolatility": iv,
                            "inTheMoney": in_the_money,
                            "expirationDate": exp_date_str,
                            "delta": round(delta, 4),
                        })

                    for oq in put_quotes:
                        strike = float(oq.strike_price)
                        iv = float(oq.implied_volatility) if oq.implied_volatility else 0.0
                        delta = _calculate_delta(current_price, strike, time_to_expiry_years, iv, False)
                        in_the_money = current_price < strike

                        all_puts.append({
                            "strike": strike,
                            "lastPrice": float(oq.last_done),
                            "bid": float(oq.last_done) * 0.95,
                            "ask": float(oq.last_done) * 1.05,
                            "volume": int(oq.volume) if oq.volume else 0,
                            "openInterest": int(oq.open_interest) if oq.open_interest else 0,
                            "impliedVolatility": iv,
                            "inTheMoney": in_the_money,
                            "expirationDate": exp_date_str,
                            "delta": round(delta, 4),
                        })

                    time.sleep(self.request_interval)

                return {
                    "ticker": ticker.upper(),
                    "currentPrice": current_price,
                    "companyName": ticker.upper(),
                    "calls": all_calls,
                    "puts": all_puts,
                    "expirationDates": [str(d) for d in valid_expiries],
                }

            except Exception as e:
                print(f"[ERROR] {ticker}: attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    self._ctx = None  # 重置连接
                continue

        return None

    def _batch_option_quote(self, symbols: list[str], chunk_size: int = 10) -> list:
        """分批获取期权报价

        长桥期权报价接口有每分钟频率限制（301607），
        使用较小 chunk + 较长间隔确保不触发。
        """
        if not symbols:
            return []

        ctx = self._get_context()
        all_quotes = []

        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            for retry in range(3):
                try:
                    quotes = ctx.option_quote(chunk)
                    all_quotes.extend(quotes)
                    break
                except Exception as e:
                    if "301607" in str(e) and retry < 2:
                        # 频率限制，等待后重试
                        wait = 5 * (retry + 1)
                        print(f"[RATE_LIMIT] waiting {wait}s before retry...")
                        time.sleep(wait)
                    else:
                        print(f"[WARN] batch option_quote failed: {e}")
                        break

            # 每批之间间隔 2 秒，避免触发频率限制
            if i + chunk_size < len(symbols):
                time.sleep(2.0)

        return all_quotes

    def get_option_data(self, ticker: str, max_cache_hours: float = 24.0) -> Optional[dict]:
        """获取期权数据（优先缓存，过期则刷新）"""
        if is_cache_fresh(ticker, max_cache_hours):
            cached = load_from_cache(ticker)
            if cached:
                return cached

        data = self.fetch_option_chain(ticker)
        if data:
            save_to_cache(ticker, data)

        return data

    def batch_update(
        self,
        tickers: list[str],
        max_cache_hours: float = 24.0,
        progress_callback=None,
    ) -> dict:
        """批量更新关注池数据（仅更新过期缓存）"""
        total = len(tickers)
        updated = 0
        skipped = 0
        failed = 0

        for i, ticker in enumerate(tickers):
            if is_cache_fresh(ticker, max_cache_hours):
                skipped += 1
                if progress_callback:
                    progress_callback(i + 1, total, ticker, "skipped")
                continue

            if updated > 0 and updated % self.batch_size == 0:
                time.sleep(self.batch_pause)

            data = self.fetch_option_chain(ticker)
            if data:
                save_to_cache(ticker, data)
                updated += 1
                if progress_callback:
                    progress_callback(i + 1, total, ticker, "updated")
            else:
                failed += 1
                if progress_callback:
                    progress_callback(i + 1, total, ticker, "failed")

            time.sleep(self.request_interval)

        return {
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "total": total,
        }
