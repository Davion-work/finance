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


def _rate_sell_put(item: dict) -> str:
    """评估 Sell Put 机会等级

    推荐标准：OTM% ≥ 7%, 年化 ≥ 20%, |Delta| ≤ 0.35, OI ≥ 100
    """
    otm = item.get("otmPercentage", 0)
    annual = item.get("annualizedReturn", 0)
    delta = abs(item.get("delta", 0))
    oi = item.get("openInterest", 0)

    if otm >= 7 and annual >= 20 and delta <= 0.35 and oi >= 100:
        return "recommended"
    return "watchlist"


def _rate_leaps_call(item: dict) -> str:
    """评估 LEAPS Call 机会等级

    推荐标准：Delta 0.55~0.75, IV < 60%, 杠杆 ≥ 3x, OI ≥ 200
    """
    delta = item.get("delta", 0)
    iv = item.get("impliedVolatility", 0)
    leverage = item.get("leverage", 0)
    oi = item.get("openInterest", 0)

    if 0.55 <= delta <= 0.75 and iv < 0.60 and leverage >= 3 and oi >= 200:
        return "recommended"
    return "watchlist"


def _build_summary(leaps: list, sell_puts: list, watchlist_size: int, scanned_count: int) -> dict:
    """生成期权机会的汇总分析结论"""
    # LEAPS Call 汇总
    leaps_tickers = sorted(set(item["ticker"] for item in leaps))
    leaps_avg_iv = 0.0
    leaps_avg_delta = 0.0
    leaps_avg_leverage = 0.0
    if leaps:
        leaps_avg_iv = sum(item["impliedVolatility"] for item in leaps) / len(leaps)
        leaps_avg_delta = sum(item["delta"] for item in leaps) / len(leaps)
        leaps_avg_leverage = sum(item["leverage"] for item in leaps) / len(leaps)

    # Sell Put 汇总
    sp_tickers = sorted(set(item["ticker"] for item in sell_puts))
    sp_avg_return = 0.0
    sp_avg_otm = 0.0
    sp_avg_iv = 0.0
    sp_avg_delta = 0.0
    if sell_puts:
        sp_avg_return = sum(item["annualizedReturn"] for item in sell_puts) / len(sell_puts)
        sp_avg_otm = sum(item["otmPercentage"] for item in sell_puts) / len(sell_puts)
        sp_avg_iv = sum(item["impliedVolatility"] for item in sell_puts) / len(sell_puts)
        sp_avg_delta = sum(item["delta"] for item in sell_puts) / len(sell_puts)

    # 高 IV 环境判断
    all_ivs = [item["impliedVolatility"] for item in leaps] + [item["impliedVolatility"] for item in sell_puts]
    overall_avg_iv = sum(all_ivs) / len(all_ivs) if all_ivs else 0
    iv_environment = "高波动" if overall_avg_iv > 0.5 else ("中等波动" if overall_avg_iv > 0.3 else "低波动")

    # 生成文字结论
    conclusions = []
    conclusions.append(f"共扫描 {scanned_count}/{watchlist_size} 个标的，"
                       f"发现 {len(leaps)} 个 LEAPS Call 机会、{len(sell_puts)} 个 Sell Put 机会。")
    conclusions.append(f"当前整体隐含波动率环境：{iv_environment}（均值 {overall_avg_iv * 100:.1f}%）。")

    sp_recommended = [item for item in sell_puts if item.get("rating") == "recommended"]
    leaps_recommended = [item for item in leaps if item.get("rating") == "recommended"]

    if sell_puts:
        conclusions.append(f"Sell Put：共 {len(sell_puts)} 个机会，其中 {len(sp_recommended)} 个达到推荐标准。")
        if sp_recommended:
            top3_sp = sp_recommended[:3]
            top_sp_names = "、".join(f"{item['ticker']}(年化{item['annualizedReturn']}%)" for item in top3_sp)
            conclusions.append(f"Sell Put 推荐操作：{top_sp_names}，平均安全边际 {sp_avg_otm:.1f}%。")
        if sp_avg_return > 50:
            conclusions.append("⚠️ 年化收益率普遍偏高，注意高收益往往伴随高风险，建议控制仓位。")

    if leaps:
        conclusions.append(f"LEAPS Call：共 {len(leaps)} 个机会，其中 {len(leaps_recommended)} 个达到推荐标准。")
        if leaps_recommended:
            top3_leaps = leaps_recommended[:3]
            top_leaps_names = "、".join(f"{item['ticker']}({item['leverage']}x杠杆)" for item in top3_leaps)
            conclusions.append(f"LEAPS Call 推荐操作：{top_leaps_names}，平均 Delta {leaps_avg_delta:.2f}。")

    if not leaps and not sell_puts:
        conclusions.append("当前无符合筛选条件的机会，可尝试调整参数或刷新数据。")

    if overall_avg_iv > 0.5:
        conclusions.append("💡 高波动环境更适合卖方策略（Sell Put），买方策略（LEAPS Call）成本偏高需谨慎。")
    elif overall_avg_iv < 0.3:
        conclusions.append("💡 低波动环境下期权较便宜，适合布局 LEAPS Call 长线看多。")

    return {
        "text": "\n".join(conclusions),
        "ivEnvironment": iv_environment,
        "overallAvgIV": round(overall_avg_iv * 100, 1),
        "leaps": {
            "count": len(leaps),
            "tickers": leaps_tickers,
            "avgIV": round(leaps_avg_iv * 100, 1),
            "avgDelta": round(leaps_avg_delta, 3),
            "avgLeverage": round(leaps_avg_leverage, 1),
        },
        "sellPut": {
            "count": len(sell_puts),
            "tickers": sp_tickers,
            "avgReturn": round(sp_avg_return, 1),
            "avgOTM": round(sp_avg_otm, 1),
            "avgIV": round(sp_avg_iv * 100, 1),
            "avgDelta": round(sp_avg_delta, 3),
        },
    }


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

    top_leaps = all_leaps[:100]
    top_sell_put = all_sell_put[:100]

    for item in top_sell_put:
        item["rating"] = _rate_sell_put(item)
    for item in top_leaps:
        item["rating"] = _rate_leaps_call(item)

    summary = _build_summary(top_leaps, top_sell_put, len(tickers), scanned_count)

    return jsonify({
        "leaps_call": top_leaps,
        "sell_put": top_sell_put,
        "summary": summary,
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
