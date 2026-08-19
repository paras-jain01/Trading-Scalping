"""
Configuration for TV Python Scanners.
All secrets loaded from environment variables (.env file locally, GitHub/Render secrets in cloud).
"""
import os
from dataclasses import dataclass
from typing import List

# Load .env if present (local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    # Telegram (REQUIRED - set in GitHub/Render secrets)
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Data source settings
    use_nsepython: bool = True  # True = NSE data via nsepython, False = yfinance
    default_timeframe: str = "1d"  # "1d" or "15m"
    lookback_days: int = 300  # For 52-week high calc

    # Pre-Breakout Scanner parameters (match Pine script exactly)
    pre_breakout = {
        "lookback_52w": 252,
        "lookback_consolid": 10,
        "lookback_obv": 50,
        "lookback_trend": 60,
        "rsi_len": 14,
        "rsi_avg_len": 20,
        "rsi_low": 40,
        "rsi_high": 65,
        "rsi_avg_min": 50,
        "ema_fast": 20,
        "ema_mid": 50,
        "ema_slow": 200,
        "vol_avg_len": 20,
        "proximity_pct": 0.25,  # 25%
        "consol_threshold": 0.15,  # 15%
    }

    # Intraday Scalper parameters (match Pine script exactly)
    intraday_scalper = {
        "ema_fast": 9,
        "ema_mid": 21,
        "ema_slow": 50,
        "ema_trend": 200,
        "rsi_len": 14,
        "rsi_low": 45,
        "rsi_high": 68,
        "vol_mult": 1.2,
        "target_pct": 0.015,  # 1.5%
        "stop_pct": 0.008,  # 0.8%
    }

    # Scan universe - liquid NSE stocks
    scan_universe: List[str] = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "BAJFINANCE",
        "TRENT", "DMART", "ADANIENT", "TATAMOTORS",
        "JIOFIN", "ZOMATO", "SBIN", "BHARTIARTL",
        "ITC", "LT", "KOTAKBANK", "HINDUNILVR",
        "ONGC", "COALINDIA", "TATASTEEL", "JSWSTEEL",
        "HINDALCO", "VEDL", "MARUTI", "SUNPHARMA",
        "AXISBANK", "INDUSINDBK", "MOTHERSON", "BHARATFORG",
        "EICHERMOT", "TVSMOTOR"
    ]

    # Minimum conditions to pass for alert
    min_conditions_pre_breakout: int = 10  # Out of 12
    min_conditions_intraday: int = 7  # Out of 8

    # Trading hours (IST)
    market_open: str = "09:15"
    market_close: str = "15:30"
    scan_time: str = "16:00"  # Post-market scan

    # Timezone
    tz: str = "Asia/Kolkata"


config = Config()


def validate_config() -> bool:
    """Check required secrets are set."""
    if not config.telegram_bot_token:
        print("⚠️  TELEGRAM_BOT_TOKEN not set")
        return False
    if not config.telegram_chat_id:
        print("⚠️  TELEGRAM_CHAT_ID not set")
        return False
    return True