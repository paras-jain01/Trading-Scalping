#!/usr/bin/env python3
"""
Quick test script to verify scanners work locally.
Run: python test_scanners.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.config import config, validate_config
from src.data import DataFetcher
from src.pre_breakout import PreBreakoutScanner
from src.intraday_scalper import IntradayScalper
from src.telegram import TelegramBot


def create_mock_daily_data(symbol: str, days: int = 300) -> pd.DataFrame:
    """Create mock daily data for testing."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Generate realistic price action with trend
    base = 1000 + np.random.randn() * 100
    returns = np.random.randn(days) * 0.015 + 0.0002  # Slight upward drift
    prices = base * np.exp(np.cumsum(returns))

    # Add some noise for OHLC
    high = prices * (1 + np.abs(np.random.randn(days)) * 0.01)
    low = prices * (1 - np.abs(np.random.randn(days)) * 0.01)
    open_ = prices * (1 + np.random.randn(days) * 0.005)
    volume = np.random.lognormal(12, 0.5, days).astype(int)

    df = pd.DataFrame({
        'Open': open_,
        'High': high,
        'Low': low,
        'Close': prices,
        'Volume': volume
    }, index=dates)

    return df


def create_mock_15m_data(symbol: str, days: int = 5) -> pd.DataFrame:
    """Create mock 15m data for testing."""
    np.random.seed(123)
    periods = days * 25  # ~25 15-min bars per day (market hours)
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='15min')

    # Filter to market hours only (9:15-15:30)
    dates = dates[(dates.time >= pd.Timestamp('09:15').time()) &
                  (dates.time <= pd.Timestamp('15:30').time())]
    dates = dates[:periods]  # Trim to exact count

    base = 1000
    returns = np.random.randn(len(dates)) * 0.003
    prices = base * np.exp(np.cumsum(returns))

    high = prices * (1 + np.abs(np.random.randn(len(dates))) * 0.003)
    low = prices * (1 - np.abs(np.random.randn(len(dates))) * 0.003)
    open_ = prices * (1 + np.random.randn(len(dates)) * 0.001)
    volume = np.random.lognormal(9, 0.5, len(dates)).astype(int)

    df = pd.DataFrame({
        'Open': open_,
        'High': high,
        'Low': low,
        'Close': prices,
        'Volume': volume
    }, index=dates[:len(prices)])

    return df


def test_pre_breakout():
    """Test Pre-Breakout Scanner with mock data."""
    print("\n" + "="*60)
    print("TESTING PRE-BREAKOUT SCANNER")
    print("="*60)

    scanner = PreBreakoutScanner()

    # Test with a few symbols
    test_symbols = ['TEST1', 'TEST2', 'TEST3']
    data_dict = {}

    for sym in test_symbols:
        df = create_mock_daily_data(sym)
        data_dict[sym] = df

    results = scanner.scan_universe(data_dict)

    for r in results:
        print(scanner.format_result(r))
        print("-" * 40)

    print(f"\nTotal scanned: {len(results)}")
    qualified = [r for r in results if r.passed]
    print(f"Qualified: {len(qualified)}")


def test_intraday_scalper():
    """Test Intraday Scalper with mock data."""
    print("\n" + "="*60)
    print("TESTING INTRADAY SCALPER")
    print("="*60)

    scalper = IntradayScalper()

    test_symbols = ['TEST1', 'TEST2']
    data_dict = {}

    for sym in test_symbols:
        df = create_mock_15m_data(sym)
        data_dict[sym] = df

    signals = run_intraday_scan(data_dict)

    for s in signals:
        print(scalper.format_signal(s))
        print("-" * 40)

    print(f"\nTotal scanned: {len(signals)}")
    buy_signals = [s for s in signals if s.buy_signal]
    sell_signals = [s for s in signals if s.sell_signal]
    print(f"Buy signals: {len(buy_signals)}")
    print(f"Sell signals: {len(sell_signals)}")


def test_telegram():
    """Test Telegram bot (requires config)."""
    print("\n" + "="*60)
    print("TESTING TELEGRAM BOT")
    print("="*60)

    if not validate_config():
        print("⚠️  Skipping - TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        print("   Set in .env or environment variables to test")
        return

    bot = TelegramBot()
    success = bot.test()
    print(f"Telegram test: {'✅ Success' if success else '❌ Failed'}")


def test_data_fetcher():
    """Test data fetcher with real symbols (if network available)."""
    print("\n" + "="*60)
    print("TESTING DATA FETCHER (Real Data)")
    print("="*60)

    fetcher = DataFetcher(use_nsepython=False)  # Use yfinance for test

    try:
        df = fetcher.fetch_daily("RELIANCE", lookback_days=60)
        if df is not None:
            print(f"✅ RELIANCE: {len(df)} bars, last close: ₹{df['Close'].iloc[-1]:.2f}")
            print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
        else:
            print("❌ Failed to fetch RELIANCE")
    except Exception as e:
        print(f"⚠️  Data fetch error (network/rate limit): {e}")


def main():
    print("🧪 TV PYTHON SCANNERS - LOCAL TEST")
    print("="*60)

    # Test with mock data (always works)
    test_pre_breakout()
    test_intraday_scalper()

    # Test Telegram (needs config)
    test_telegram()

    # Test real data fetch (needs network)
    test_data_fetcher()

    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()