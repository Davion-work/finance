"""期权机会分析发现 - Web 服务入口"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from data.fetcher import OptionDataFetcher
from data.watchlist import get_active_tickers, add_tickers, remove_tickers
from data.cache import load_from_cache, get_cache_status
from strategies.leaps_call import LeapsCallStrategy
from strategies.sell_put import SellPutStrategy

app = Flask(__name__, static_folder=None)

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# 后台刷新状态
_refresh_status = {"running": False, "progress": 0, "total": 0, "current": "", "result": None}
_refresh_lock = threading.Lock()


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    """提供 web/static 目录下的静态资源"""
    return send_from_directory(os.path.join(WEB_DIR, "static"), filename)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


@app.route("/api/scan", methods=["POST"])
def scan_opportunities():
    """基于本地缓存数据全量扫描期权机会

    从缓存中读取关注池所有标的的期权数据，运行策略分析。
    不触发网络请求，纯本地计算，毫秒级响应。
    """
    leaps_strategy = LeapsCallStrategy()
    sell_put_strategy = SellPutStrategy()

    tickers = get_active_tickers()
    all_leaps = []
    all_sell_put = []
    scanned_count = 0

    for ticker in tickers:
        option_data = load_from_cache(ticker)
        if not option_data:
            continue

        scanned_count += 1

        leaps_results = leaps_strategy.analyze(option_data)
        all_leaps.extend(leaps_results)

        sell_put_results = sell_put_strategy.analyze(option_data)
        all_sell_put.extend(sell_put_results)

    all_leaps.sort(key=lambda x: x["leverage"], reverse=True)
    all_sell_put.sort(key=lambda x: x["annualizedReturn"], reverse=True)

    return jsonify({
        "leaps_call": all_leaps[:100],
        "sell_put": all_sell_put[:100],
        "meta": {
            "watchlistSize": len(tickers),
            "scannedFromCache": scanned_count,
        }
    })


@app.route("/api/refresh", methods=["POST"])
def refresh_data():
    """触发后台批量刷新关注池数据

    增量更新：仅刷新缓存已过期的标的。
    """
    with _refresh_lock:
        if _refresh_status["running"]:
            return jsonify({"status": "already_running", "progress": _refresh_status}), 409

    def _run_refresh():
        with _refresh_lock:
            _refresh_status["running"] = True
            _refresh_status["progress"] = 0
            _refresh_status["result"] = None

        tickers = get_active_tickers()
        _refresh_status["total"] = len(tickers)

        def on_progress(current, total, ticker, status):
            _refresh_status["progress"] = current
            _refresh_status["current"] = f"{ticker} ({status})"

        fetcher = OptionDataFetcher(request_interval=1.5, batch_pause=8.0, batch_size=8)
        result = fetcher.batch_update(tickers, max_cache_hours=24.0, progress_callback=on_progress)

        with _refresh_lock:
            _refresh_status["running"] = False
            _refresh_status["result"] = result

    thread = threading.Thread(target=_run_refresh, daemon=True)
    thread.start()

    return jsonify({"status": "started", "totalTickers": len(get_active_tickers())})


@app.route("/api/refresh/status")
def refresh_status():
    """查询后台刷新进度"""
    return jsonify(_refresh_status)


@app.route("/api/cache/status")
def cache_status():
    """查询缓存状态"""
    return jsonify(get_cache_status())


@app.route("/api/watchlist")
def get_watchlist():
    """获取当前关注池列表"""
    tickers = get_active_tickers()
    return jsonify({"tickers": tickers, "count": len(tickers)})


@app.route("/api/watchlist/add", methods=["POST"])
def add_to_watchlist():
    """添加标的到关注池"""
    body = request.get_json(silent=True) or {}
    tickers = body.get("tickers", [])
    if not tickers:
        return jsonify({"error": "tickers required"}), 400
    add_tickers(tickers)
    return jsonify({"status": "ok", "added": tickers, "totalCount": len(get_active_tickers())})


@app.route("/api/watchlist/remove", methods=["POST"])
def remove_from_watchlist():
    """从关注池移除标的"""
    body = request.get_json(silent=True) or {}
    tickers = body.get("tickers", [])
    if not tickers:
        return jsonify({"error": "tickers required"}), 400
    remove_tickers(tickers)
    return jsonify({"status": "ok", "removed": tickers, "totalCount": len(get_active_tickers())})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
