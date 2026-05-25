"""期权数据获取模块 - 统一入口

根据 .longbridgeapi 中的 DATA_SOURCE 配置自动选择数据源：
- longport: 长桥 OpenAPI（推荐，实时 L1 行情）
- yahoo: Yahoo Finance（备用）

对外暴露 OptionDataFetcher 类，策略层无需感知底层数据源差异。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载配置以确定数据源
_PROJECT_DIR = Path(__file__).resolve().parent.parent
_CREDENTIAL_FILE = _PROJECT_DIR / ".longbridgeapi"
if _CREDENTIAL_FILE.exists():
    load_dotenv(_CREDENTIAL_FILE)

DATA_SOURCE = os.environ.get("DATA_SOURCE", "yahoo").strip().lower()

if DATA_SOURCE == "longport":
    from data.fetcher_longport import LongportOptionDataFetcher as OptionDataFetcher
else:
    from data._fetcher_yahoo import OptionDataFetcher  # noqa: F401
