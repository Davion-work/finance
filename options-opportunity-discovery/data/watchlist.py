"""关注池管理模块

维护一个本地关注列表，默认包含 S&P 500 成分股，支持用户自定义增删。
"""

import json
import os
from pathlib import Path

DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = DATA_DIR / "watchlist.json"

# S&P 500 高流动性期权标的（精选 ~100 只最活跃的期权股票）
# 完整 500 只可以后续扩展，初期用高流动性子集确保数据质量
SP500_CORE = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "JPM", "V", "XOM", "PG", "MA", "HD", "CVX", "MRK",
    "ABBV", "LLY", "PEP", "KO", "AVGO", "COST", "WMT", "MCD", "CSCO",
    "ACN", "TMO", "ABT", "DHR", "NKE", "LIN", "NEE", "PM", "TXN", "UNP",
    "RTX", "LOW", "AMGN", "HON", "UPS", "QCOM", "BA", "GS", "CAT", "SBUX",
    "IBM", "AMD", "INTC", "GE", "AMAT", "ISRG", "NOW", "ADP", "BKNG",
    "MDLZ", "ADI", "GILD", "SYK", "MMC", "LRCX", "DE", "REGN", "VRTX",
    "CI", "ZTS", "BDX", "CME", "CB", "PLD", "SO", "DUK", "CL", "MO",
    "APD", "SLB", "USB", "TGT", "PNC", "SCHW", "AXP", "COP", "EOG",
    "ABNB", "PANW", "CRWD", "SNOW", "SQ", "SHOP", "NET", "DDOG", "ZS",
    "COIN", "MARA", "PLTR", "SOFI", "RIVN", "LCID", "NIO", "ARM", "SMCI",
]


def load_watchlist() -> dict:
    """加载关注池配置

    Returns:
        {"tickers": [...], "custom_added": [...], "custom_removed": [...]}
    """
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "base": "sp500_core",
        "custom_added": [],
        "custom_removed": [],
    }


def save_watchlist(config: dict):
    """保存关注池配置"""
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_active_tickers() -> list[str]:
    """获取当前生效的关注池标的列表"""
    config = load_watchlist()
    base_tickers = set(SP500_CORE)

    # 应用用户自定义
    custom_added = set(config.get("custom_added", []))
    custom_removed = set(config.get("custom_removed", []))

    active = (base_tickers | custom_added) - custom_removed
    return sorted(active)


def add_tickers(tickers: list[str]):
    """添加自定义标的到关注池"""
    config = load_watchlist()
    existing = set(config.get("custom_added", []))
    removed = set(config.get("custom_removed", []))

    for ticker in tickers:
        ticker_upper = ticker.upper().strip()
        existing.add(ticker_upper)
        removed.discard(ticker_upper)

    config["custom_added"] = sorted(existing)
    config["custom_removed"] = sorted(removed)
    save_watchlist(config)


def remove_tickers(tickers: list[str]):
    """从关注池移除标的"""
    config = load_watchlist()
    added = set(config.get("custom_added", []))
    removed = set(config.get("custom_removed", []))

    for ticker in tickers:
        ticker_upper = ticker.upper().strip()
        removed.add(ticker_upper)
        added.discard(ticker_upper)

    config["custom_added"] = sorted(added)
    config["custom_removed"] = sorted(removed)
    save_watchlist(config)
