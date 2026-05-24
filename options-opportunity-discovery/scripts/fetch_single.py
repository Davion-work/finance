# -*- coding: utf-8 -*-
"""手动获取单个标的的期权数据并缓存"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import OptionDataFetcher
from data.cache import is_cache_fresh

ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

fetcher = OptionDataFetcher(request_interval=2.0)
print(f"Fetching {ticker} option chain...")
data = fetcher.get_option_data(ticker, max_cache_hours=0.01)

if data:
    calls_count = len(data.get("calls", []))
    puts_count = len(data.get("puts", []))
    price = data.get("currentPrice", "N/A")
    exp_count = len(data.get("expirationDates", []))
    print(f"Success!")
    print(f"  Ticker: {ticker}")
    print(f"  Price: ${price}")
    print(f"  Expiry dates: {exp_count}")
    print(f"  Call contracts: {calls_count}")
    print(f"  Put contracts: {puts_count}")
    print(f"  Cached: {is_cache_fresh(ticker)}")
else:
    print(f"Failed to fetch data for {ticker}")
