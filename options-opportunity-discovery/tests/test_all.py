# -*- coding: utf-8 -*-
"""Options Opportunity Discovery - Integration Test Suite

Validates:
1. BSM Delta calculation correctness
2. LEAPS Call strategy filtering logic (with list[dict] input)
3. Sell Put strategy filtering logic (with list[dict] input)
4. Flask API routes return proper JSON (scan based on cache)
5. Watchlist management
6. Cache read/write
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import OptionDataFetcher
from data.watchlist import get_active_tickers, SP500_CORE
from data.cache import (
    save_to_cache, load_from_cache, is_cache_fresh,
    get_cache_status, CACHE_DIR, ensure_cache_dir
)
from strategies.leaps_call import LeapsCallStrategy, calculate_bsm_delta
from strategies.sell_put import SellPutStrategy


def test_bsm_delta():
    """Validate BSM Delta calculation"""
    print("=" * 50)
    print("[TEST] BSM Delta calculation")

    delta = calculate_bsm_delta(
        spot=100, strike=100, time_to_expiry_years=1.0,
        risk_free_rate=0.045, implied_vol=0.30
    )
    assert 0.5 < delta < 0.75, f"ATM Delta unexpected: {delta}"
    print(f"  ATM (S=100, K=100, T=1y, IV=30%): Delta = {delta:.4f} [OK]")

    delta_itm = calculate_bsm_delta(
        spot=150, strike=100, time_to_expiry_years=1.0,
        risk_free_rate=0.045, implied_vol=0.30
    )
    assert delta_itm > 0.9, f"Deep ITM Delta unexpected: {delta_itm}"
    print(f"  Deep ITM (S=150, K=100): Delta = {delta_itm:.4f} [OK]")

    delta_otm = calculate_bsm_delta(
        spot=50, strike=100, time_to_expiry_years=1.0,
        risk_free_rate=0.045, implied_vol=0.30
    )
    assert delta_otm < 0.1, f"Deep OTM Delta unexpected: {delta_otm}"
    print(f"  Deep OTM (S=50, K=100): Delta = {delta_otm:.4f} [OK]")

    delta_zero = calculate_bsm_delta(spot=0, strike=100, time_to_expiry_years=1.0,
                                      risk_free_rate=0.045, implied_vol=0.30)
    assert delta_zero == 0.0
    print(f"  Edge (spot=0): Delta = {delta_zero} [OK]")

    print("[PASS] BSM Delta calculation\n")


def test_leaps_strategy_with_list_input():
    """Validate LEAPS Call strategy with list[dict] input (cache format)"""
    print("=" * 50)
    print("[TEST] LEAPS Call strategy (list[dict] input)")

    from datetime import datetime, timedelta

    future_date = (datetime.now() + timedelta(days=400)).strftime("%Y-%m-%d")
    near_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    mock_calls = [
        {"strike": 180, "lastPrice": 35.0, "bid": 34.0, "ask": 36.0,
         "impliedVolatility": 0.35, "openInterest": 500, "volume": 100,
         "expirationDate": future_date},
        {"strike": 180, "lastPrice": 5.0, "bid": 4.5, "ask": 5.5,
         "impliedVolatility": 0.35, "openInterest": 500, "volume": 100,
         "expirationDate": near_date},
        {"strike": 180, "lastPrice": 35.0, "bid": 34.0, "ask": 36.0,
         "impliedVolatility": 0.35, "openInterest": 10, "volume": 2,
         "expirationDate": future_date},
        {"strike": 180, "lastPrice": 50.0, "bid": 49.0, "ask": 51.0,
         "impliedVolatility": 0.95, "openInterest": 500, "volume": 100,
         "expirationDate": future_date},
    ]

    option_data = {
        "ticker": "AAPL",
        "currentPrice": 200.0,
        "calls": mock_calls,
        "puts": [],
    }

    strategy = LeapsCallStrategy(min_days_to_expiry=180, min_open_interest=100,
                                  max_implied_volatility=0.80)
    results = strategy.analyze(option_data)

    print(f"  Input 4 rows, filtered: {len(results)} rows")
    assert len(results) <= 1
    if results:
        assert results[0]["daysToExpiry"] > 180
        assert results[0]["openInterest"] >= 100
        assert "delta" in results[0]
        print(f"  Selected: strike={results[0]['strike']}, delta={results[0]['delta']} [OK]")
    else:
        print("  No contracts matched (delta out of range) [OK]")

    empty_result = strategy.analyze({"ticker": "X", "currentPrice": 0, "calls": []})
    assert empty_result == []
    print("  Empty data guard [OK]")

    print("[PASS] LEAPS Call strategy\n")


def test_sell_put_strategy_with_list_input():
    """Validate Sell Put strategy with list[dict] input (cache format)"""
    print("=" * 50)
    print("[TEST] Sell Put strategy (list[dict] input)")

    from datetime import datetime, timedelta

    exp_date_good = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d")
    exp_date_far = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")

    mock_puts = [
        {"strike": 180, "bid": 3.5, "ask": 4.0,
         "impliedVolatility": 0.30, "openInterest": 200, "volume": 50,
         "expirationDate": exp_date_good},
        {"strike": 180, "bid": 8.0, "ask": 9.0,
         "impliedVolatility": 0.30, "openInterest": 200, "volume": 50,
         "expirationDate": exp_date_far},
        {"strike": 170, "bid": 0, "ask": 0.05,
         "impliedVolatility": 0.30, "openInterest": 200, "volume": 50,
         "expirationDate": exp_date_good},
        {"strike": 198, "bid": 5.0, "ask": 5.5,
         "impliedVolatility": 0.30, "openInterest": 200, "volume": 50,
         "expirationDate": exp_date_good},
    ]

    option_data = {
        "ticker": "AAPL",
        "currentPrice": 200.0,
        "calls": [],
        "puts": mock_puts,
    }

    strategy = SellPutStrategy(min_annualized_return=0.10, min_otm_percentage=0.05,
                                max_otm_percentage=0.30, min_days_to_expiry=20,
                                max_days_to_expiry=60, min_open_interest=50)
    results = strategy.analyze(option_data)

    print(f"  Input 4 rows, filtered: {len(results)} rows")
    for r in results:
        assert r["otmPercentage"] >= 5.0
        assert r["annualizedReturn"] >= 10.0
        print(f"  Selected: strike={r['strike']}, OTM={r['otmPercentage']}%, "
              f"annual={r['annualizedReturn']}% [OK]")

    empty_result = strategy.analyze({"ticker": "X", "currentPrice": None, "puts": []})
    assert empty_result == []
    print("  Empty data guard [OK]")

    print("[PASS] Sell Put strategy\n")


def test_cache_operations():
    """Validate cache save/load/freshness check"""
    print("=" * 50)
    print("[TEST] Cache operations")

    test_data = {
        "ticker": "TEST",
        "currentPrice": 150.0,
        "companyName": "Test Corp",
        "expirationDates": ["2026-06-20", "2026-07-18"],
        "calls": [{"strike": 140, "lastPrice": 12.0, "expirationDate": "2026-06-20"}],
        "puts": [{"strike": 160, "bid": 11.0, "expirationDate": "2026-06-20"}],
    }

    save_to_cache("TEST", test_data)
    print("  save_to_cache [OK]")

    loaded = load_from_cache("TEST")
    assert loaded is not None
    assert loaded["ticker"] == "TEST"
    assert loaded["currentPrice"] == 150.0
    assert len(loaded["calls"]) == 1
    assert len(loaded["puts"]) == 1
    print("  load_from_cache [OK]")

    assert is_cache_fresh("TEST", max_age_hours=1.0) is True
    assert is_cache_fresh("NONEXISTENT", max_age_hours=1.0) is False
    print("  is_cache_fresh [OK]")

    status = get_cache_status()
    assert status["totalCached"] >= 1
    print(f"  Cache status: {status['totalCached']} cached, {status['freshCount']} fresh [OK]")

    # Cleanup
    cache_path = CACHE_DIR / "TEST.json"
    if cache_path.exists():
        cache_path.unlink()

    print("[PASS] Cache operations\n")


def test_watchlist():
    """Validate watchlist management"""
    print("=" * 50)
    print("[TEST] Watchlist")

    tickers = get_active_tickers()
    assert len(tickers) > 50, f"Expected 50+ tickers in default pool, got {len(tickers)}"
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    print(f"  Default pool: {len(tickers)} tickers [OK]")
    print(f"  SP500_CORE defined: {len(SP500_CORE)} tickers [OK]")

    print("[PASS] Watchlist\n")


def test_flask_api():
    """Validate Flask API routes"""
    print("=" * 50)
    print("[TEST] Flask API routes")

    from server import app

    client = app.test_client()

    # Health check
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
    print("  GET /api/health => 200 [OK]")

    # Index
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<!DOCTYPE html>" in resp.data
    print("  GET / => 200, HTML [OK]")

    # Scan (from cache, may return empty if no cache)
    resp = client.post("/api/scan")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "leaps_call" in data
    assert "sell_put" in data
    assert "meta" in data
    assert isinstance(data["leaps_call"], list)
    assert isinstance(data["sell_put"], list)
    assert b"<!DOCTYPE" not in resp.data
    print(f"  POST /api/scan => 200, JSON, scanned={data['meta']['scannedFromCache']} [OK]")

    # Cache status
    resp = client.get("/api/cache/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "totalCached" in data
    print(f"  GET /api/cache/status => 200 [OK]")

    # Watchlist
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "tickers" in data
    assert data["count"] > 0
    print(f"  GET /api/watchlist => 200, count={data['count']} [OK]")

    # 404
    resp = client.get("/nonexistent-page")
    assert resp.status_code == 404
    print("  GET /nonexistent => 404 [OK]")

    print("[PASS] Flask API routes\n")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Options Opportunity Discovery - Test Suite")
    print("=" * 50 + "\n")

    passed = 0
    failed = 0
    tests = [
        test_bsm_delta,
        test_leaps_strategy_with_list_input,
        test_sell_put_strategy_with_list_input,
        test_cache_operations,
        test_watchlist,
        test_flask_api,
    ]

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_func.__name__}: {e}\n")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_func.__name__}: {type(e).__name__}: {e}\n")
            failed += 1

    print("=" * 50)
    print(f"  Result: {passed} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
