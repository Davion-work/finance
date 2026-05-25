"""关注池管理模块

维护一个本地关注列表，默认包含 S&P 500 成分股，支持用户自定义增删。
"""

import json
import os
from pathlib import Path

DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = DATA_DIR / "watchlist.json"

# 默认关注池：AI + 中国科技（美股上市，20只）
# 港股无个股期权数据，Sell Put 策略聚焦美股
DEFAULT_WATCHLIST = [
    "BABA",   # 阿里巴巴
    "JD",     # 京东
    "BIDU",   # 百度
    "PDD",    # 拼多多
    "NIO",    # 蔚来
    "XPEV",   # 小鹏汽车
    "LI",     # 理想汽车
    "BILI",   # 哔哩哔哩
    "TME",    # 腾讯音乐
    "GDS",    # 万国数据
    "NVDA",   # 英伟达
    "AMD",    # AMD
    "SMCI",   # 超微电脑
    "ARM",    # ARM
    "PLTR",   # Palantir
    "AVGO",   # 博通
    "TSM",    # 台积电
    "MSFT",   # 微软
    "GOOGL",  # 谷歌
    "META",   # Meta
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
    base_tickers = set(DEFAULT_WATCHLIST)

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
