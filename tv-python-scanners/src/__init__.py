"""
TV Python Scanners - Free cloud-native trading scanners.
Port of TradingView Pine Scripts to Python for GitHub Actions + Render deployment.
"""

__version__ = "1.0.0"
__author__ = "TV Python Scanners"

from src.config import config, validate_config
from src.data import get_data_fetcher
from src.pre_breakout import PreBreakoutScanner, run_pre_breakout_scan, ScanResult
from src.intraday_scalper import IntradayScalper, run_intraday_scan, ScalperSignal
from src.telegram import TelegramBot, get_bot, send_telegram

__all__ = [
    'config',
    'validate_config',
    'get_data_fetcher',
    'PreBreakoutScanner',
    'run_pre_breakout_scan',
    'ScanResult',
    'IntradayScalper',
    'run_intraday_scan',
    'ScalperSignal',
    'TelegramBot',
    'get_bot',
    'send_telegram',
]