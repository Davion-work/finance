"""本地缓存管理模块

将期权数据缓存到本地 JSON 文件，避免重复请求 Yahoo Finance。
支持增量更新和缓存过期判断。
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "cache"


def ensure_cache_dir():
    """确保缓存目录存在"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_path(ticker: str) -> Path:
    """获取指定标的的缓存文件路径"""
    return CACHE_DIR / f"{ticker.upper()}.json"


def get_cache_meta_path() -> Path:
    """获取缓存元信息文件路径"""
    return CACHE_DIR / "_meta.json"


def is_cache_fresh(ticker: str, max_age_hours: float = 24.0) -> bool:
    """判断缓存是否仍然有效

    Args:
        ticker: 股票代码
        max_age_hours: 最大缓存有效时间（小时），默认 24 小时

    Returns:
        True 表示缓存仍有效，False 表示需要刷新
    """
    cache_path = get_cache_path(ticker)
    if not cache_path.exists():
        return False

    file_mtime = os.path.getmtime(cache_path)
    age_hours = (time.time() - file_mtime) / 3600
    return age_hours < max_age_hours


def save_to_cache(ticker: str, data: dict):
    """将期权数据保存到本地缓存

    Args:
        ticker: 股票代码
        data: 期权数据（需要序列化为 JSON 兼容格式）
    """
    ensure_cache_dir()
    cache_path = get_cache_path(ticker)

    cache_entry = {
        "ticker": ticker,
        "cachedAt": datetime.now().isoformat(),
        "currentPrice": data.get("currentPrice"),
        "companyName": data.get("companyName"),
        "expirationDates": data.get("expirationDates", []),
        "calls": data.get("calls"),
        "puts": data.get("puts"),
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_entry, f, ensure_ascii=False)

    _update_meta(ticker)


def load_from_cache(ticker: str) -> Optional[dict]:
    """从本地缓存加载期权数据

    Args:
        ticker: 股票代码

    Returns:
        缓存的期权数据字典，不存在则返回 None
    """
    cache_path = get_cache_path(ticker)
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_cache_status() -> dict:
    """获取缓存整体状态信息"""
    ensure_cache_dir()
    meta_path = get_cache_meta_path()

    cached_files = list(CACHE_DIR.glob("*.json"))
    cached_tickers = [f.stem for f in cached_files if f.stem != "_meta"]

    last_update = None
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                last_update = meta.get("lastFullUpdate")
        except (json.JSONDecodeError, OSError):
            pass

    fresh_count = sum(1 for t in cached_tickers if is_cache_fresh(t))

    return {
        "totalCached": len(cached_tickers),
        "freshCount": fresh_count,
        "staleCount": len(cached_tickers) - fresh_count,
        "lastFullUpdate": last_update,
        "cacheDir": str(CACHE_DIR),
    }


def clear_cache():
    """清除所有缓存"""
    ensure_cache_dir()
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()


def _update_meta(ticker: str):
    """更新缓存元信息"""
    meta_path = get_cache_meta_path()
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            meta = {}

    meta["lastUpdate"] = datetime.now().isoformat()
    meta["lastTicker"] = ticker

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
