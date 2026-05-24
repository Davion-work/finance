"""期权数据获取模块 - 从 Yahoo Finance 获取期权链数据

支持：
- 单个标的实时获取
- 批量抓取（带限流控制 + User-Agent 轮换）
- 与本地缓存配合的增量更新
- 自动重试（指数退避）
"""

import time
import random
import requests
import yfinance as yf
import pandas as pd
from typing import Optional
from data.cache import is_cache_fresh, save_to_cache, load_from_cache

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


def _create_session() -> requests.Session:
    """创建带随机 User-Agent 的 requests session"""
    session = requests.Session()
    session.headers["User-Agent"] = random.choice(USER_AGENTS)
    return session


class OptionDataFetcher:
    """从 Yahoo Finance 获取期权数据，配合本地缓存使用"""

    def __init__(
        self,
        request_interval: float = 2.0,
        batch_pause: float = 10.0,
        batch_size: int = 5,
        max_retries: int = 3,
    ):
        """
        Args:
            request_interval: 每次请求间隔（秒），避免限流
            batch_pause: 每批次之间的暂停时间（秒）
            batch_size: 每批次处理的标的数量
            max_retries: 单个标的最大重试次数
        """
        self.request_interval = request_interval
        self.batch_pause = batch_pause
        self.batch_size = batch_size
        self.max_retries = max_retries

    def fetch_option_chain(self, ticker: str) -> Optional[dict]:
        """从 Yahoo Finance 实时获取指定标的的完整期权链数据

        使用随机 User-Agent + 指数退避重试机制。

        Args:
            ticker: 股票代码，如 'AAPL'

        Returns:
            包含 calls/puts 列表及标的信息的字典，失败返回 None
        """
        for attempt in range(self.max_retries):
            try:
                session = _create_session()
                stock = yf.Ticker(ticker, session=session)
                info = stock.info
                current_price = info.get("currentPrice") or info.get("regularMarketPrice")

                if not current_price or current_price <= 0:
                    return None

                expiration_dates = stock.options
                if not expiration_dates:
                    return None

                all_calls = []
                all_puts = []

                for exp_date in expiration_dates:
                    chain = stock.option_chain(exp_date)
                    calls_df = chain.calls.copy()
                    puts_df = chain.puts.copy()
                    calls_df["expirationDate"] = exp_date
                    puts_df["expirationDate"] = exp_date
                    all_calls.append(calls_df)
                    all_puts.append(puts_df)

                calls_combined = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
                puts_combined = pd.concat(all_puts, ignore_index=True) if all_puts else pd.DataFrame()

                return {
                    "ticker": ticker,
                    "currentPrice": current_price,
                    "companyName": info.get("shortName", ticker),
                    "calls": calls_combined.to_dict(orient="records"),
                    "puts": puts_combined.to_dict(orient="records"),
                    "expirationDates": list(expiration_dates),
                }
            except Exception as e:
                error_msg = str(e)
                is_rate_limited = "Too Many Requests" in error_msg or "429" in error_msg

                if is_rate_limited and attempt < self.max_retries - 1:
                    # 指数退避: 30s, 60s, 120s
                    wait_time = 30 * (2 ** attempt) + random.uniform(0, 10)
                    print(f"[WARN] {ticker}: Rate limited, retry {attempt + 1}/{self.max_retries} "
                          f"after {wait_time:.0f}s")
                    time.sleep(wait_time)
                    continue

                print(f"[ERROR] Failed to fetch option data for {ticker}: {e}")
                return None

        return None

    def get_option_data(self, ticker: str, max_cache_hours: float = 24.0) -> Optional[dict]:
        """获取期权数据（优先缓存，过期则刷新）

        Args:
            ticker: 股票代码
            max_cache_hours: 缓存有效时间

        Returns:
            期权数据字典，calls/puts 为 list[dict] 格式
        """
        if is_cache_fresh(ticker, max_cache_hours):
            cached = load_from_cache(ticker)
            if cached:
                return cached

        data = self.fetch_option_chain(ticker)
        if data:
            save_to_cache(ticker, data)
            time.sleep(self.request_interval)

        return data

    def batch_update(
        self,
        tickers: list[str],
        max_cache_hours: float = 24.0,
        progress_callback=None,
    ) -> dict:
        """批量更新关注池数据（仅更新过期缓存）

        Args:
            tickers: 标的列表
            max_cache_hours: 缓存有效时间
            progress_callback: 进度回调 fn(current, total, ticker, status)

        Returns:
            {"updated": int, "skipped": int, "failed": int, "total": int}
        """
        total = len(tickers)
        updated = 0
        skipped = 0
        failed = 0

        for i, ticker in enumerate(tickers):
            # 缓存仍有效则跳过
            if is_cache_fresh(ticker, max_cache_hours):
                skipped += 1
                if progress_callback:
                    progress_callback(i + 1, total, ticker, "skipped")
                continue

            # 批次暂停
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
