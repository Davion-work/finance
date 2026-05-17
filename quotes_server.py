"""
Options Quote Server
====================
本地 Flask 后端，从 Yahoo Finance / AKShare 抓取实时期权链数据，
供 options-quotes.html 前端调用。

使用方法
-------
1. 安装依赖:
   pip install flask flask-cors yfinance
   # 如要查询 A 股 50ETF / 300ETF 期权:
   pip install akshare

2. 启动:
   python quotes_server.py

3. 浏览器打开 options-quotes.html

API 端点
-------
GET /api/health                              健康检查
GET /api/spot?symbol=AAPL                    现价 + 涨跌
GET /api/expirations?symbol=AAPL             所有到期日
GET /api/chain?symbol=AAPL&date=YYYY-MM-DD   期权链 (Calls + Puts)

支持市场
-------
- 美股 (yfinance): AAPL, NVDA, SPY, QQQ, TSLA 等
- 港股 (yfinance): 0700.HK, 9988.HK 等
- A股 50ETF/300ETF期权 (akshare 可选)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import math
import sys

app = Flask(__name__)
CORS(app)

# yfinance for US/HK options
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# akshare for A-share options (optional)
try:
    import akshare as ak
    HAS_AK = True
except ImportError:
    HAS_AK = False


def safe_float(v, decimals=4):
    """Convert to float, replacing NaN/inf with 0."""
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return round(f, decimals)
    except (TypeError, ValueError):
        return 0.0


def safe_int(v):
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return 0
        return int(v)
    except (TypeError, ValueError):
        return 0


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'yfinance': HAS_YF,
        'akshare': HAS_AK,
        'version': '1.0',
        'message': '后端运行正常' if HAS_YF else 'yfinance 未安装',
    })


@app.route('/api/spot')
def spot():
    symbol = request.args.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'symbol 参数必填'}), 400
    if not HAS_YF:
        return jsonify({'error': 'yfinance 未安装。请运行: pip install yfinance'}), 500

    try:
        t = yf.Ticker(symbol)
        price = prev = currency = name = None

        try:
            fi = t.fast_info
            price = fi.last_price
            prev = fi.previous_close
            currency = fi.currency
        except Exception:
            pass

        if price is None:
            try:
                info = t.info
                price = info.get('regularMarketPrice') or info.get('currentPrice')
                prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
                currency = info.get('currency', 'USD')
                name = info.get('shortName') or info.get('longName')
            except Exception:
                pass

        if price is None:
            return jsonify({'error': f'未找到 {symbol} 的报价'}), 404

        change = (price - prev) if prev else 0
        change_pct = (change / prev * 100) if prev else 0

        return jsonify({
            'symbol': symbol,
            'name': name or symbol,
            'price': safe_float(price, 2),
            'previousClose': safe_float(prev, 2),
            'change': safe_float(change, 2),
            'changePct': safe_float(change_pct, 2),
            'currency': currency or 'USD',
        })
    except Exception as e:
        return jsonify({'error': f'获取 {symbol} 报价失败: {str(e)}'}), 500


@app.route('/api/expirations')
def expirations():
    symbol = request.args.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'symbol 参数必填'}), 400
    if not HAS_YF:
        return jsonify({'error': 'yfinance 未安装'}), 500

    try:
        t = yf.Ticker(symbol)
        dates = list(t.options)
        if not dates:
            return jsonify({'error': f'{symbol} 暂无期权数据'}), 404
        return jsonify({'symbol': symbol, 'dates': dates})
    except Exception as e:
        return jsonify({'error': f'获取到期日失败: {str(e)}'}), 500


@app.route('/api/chain')
def chain():
    symbol = request.args.get('symbol', '').strip().upper()
    date = request.args.get('date', '').strip()

    if not symbol or not date:
        return jsonify({'error': 'symbol 和 date 参数必填'}), 400
    if not HAS_YF:
        return jsonify({'error': 'yfinance 未安装'}), 500

    try:
        t = yf.Ticker(symbol)
        ch = t.option_chain(date)

        # 获取现价用于 ITM 标记
        spot_price = None
        try:
            spot_price = t.fast_info.last_price
        except Exception:
            try:
                info = t.info
                spot_price = info.get('regularMarketPrice') or info.get('currentPrice')
            except Exception:
                pass

        cols = ['strike', 'lastPrice', 'bid', 'ask', 'volume',
                'openInterest', 'impliedVolatility', 'inTheMoney']

        def clean(df):
            available = [c for c in cols if c in df.columns]
            records = []
            for _, row in df[available].iterrows():
                rec = {}
                for c in available:
                    v = row[c]
                    if c in ('volume', 'openInterest'):
                        rec[c] = safe_int(v)
                    elif c == 'inTheMoney':
                        rec[c] = bool(v) if v is not None else False
                    elif c == 'impliedVolatility':
                        rec[c] = safe_float(v, 4)
                    else:
                        rec[c] = safe_float(v, 4)
                records.append(rec)
            return records

        calls = clean(ch.calls)
        puts = clean(ch.puts)

        # 排序：行权价升序
        calls.sort(key=lambda r: r['strike'])
        puts.sort(key=lambda r: r['strike'])

        return jsonify({
            'symbol': symbol,
            'date': date,
            'spot': safe_float(spot_price, 2) if spot_price else None,
            'calls': calls,
            'puts': puts,
        })
    except Exception as e:
        return jsonify({'error': f'获取期权链失败: {str(e)}'}), 500


def banner():
    yf_status = '✓ 已安装' if HAS_YF else '✗ 未安装  (运行: pip install yfinance)'
    ak_status = '✓ 已安装' if HAS_AK else '✗ 可选    (A股期权需 pip install akshare)'
    print("=" * 64)
    print("  期权实时行情后端 · Options Quote Server")
    print("=" * 64)
    print(f"  yfinance : {yf_status}")
    print(f"  akshare  : {ak_status}")
    print(f"  flask    : ✓ 已安装")
    print()
    print(f"  服务地址 : http://localhost:5000")
    print(f"  健康检查 : http://localhost:5000/api/health")
    print()
    print(f"  在浏览器打开 options-quotes.html 即可使用")
    print(f"  按 Ctrl+C 停止服务")
    print("=" * 64)
    if not HAS_YF:
        print()
        print("  ⚠️  缺少 yfinance，部分功能不可用")
        print("  请运行: pip install yfinance flask flask-cors")
        print()


if __name__ == '__main__':
    banner()
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n  服务已停止。")
        sys.exit(0)
