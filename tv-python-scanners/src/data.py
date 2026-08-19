"""
Data fetching module for NSE stocks.
Supports yfinance (global) and nsepython (India-specific) backends.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from src.config import config

logger = logging.getLogger(__name__)


class DataFetcher:
    """Unified data fetcher for daily and intraday data."""

    def __init__(self, use_nsepython: bool = True):
        self.use_nsepython = use_nsepython
        self._nse = None
        self._yf_cache = {}

    def _get_nse(self):
        """Lazy load nsepython."""
        if self._nse is None and self.use_nsepython:
            try:
                from nsepython import nse_eq
                self._nse = nse_eq
            except ImportError:
                logger.warning("nsepython not available, falling back to yfinance")
                self.use_nsepython = False
        return self._nse

    def _symbol_yfinance(self, symbol: str) -> str:
        """Convert NSE symbol to yfinance format."""
        if symbol.endswith(".NS"):
            return symbol
        return f"{symbol}.NS"

    def _symbol_nsepython(self, symbol: str) -> str:
        """Convert to nsepython format (just symbol)."""
        return symbol.replace(".NS", "")

    def fetch_daily(self, symbol: str, lookback_days: int = 300) -> Optional[pd.DataFrame]:
        """
        Fetch daily OHLCV data.
        Returns DataFrame with columns: Open, High, Low, Close, Volume
        Index: DatetimeIndex (date only)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 10)  # Extra for indicators

        try:
            if self.use_nsepython:
                return self._fetch_daily_nse(symbol, start_date, end_date)
            else:
                return self._fetch_daily_yf(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"Error fetching daily data for {symbol}: {e}")
            # Try fallback
            if self.use_nsepython:
                self.use_nsepython = False
                return self.fetch_daily(symbol, lookback_days)
            return None

    def _fetch_daily_nse(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch daily data via nsepython."""
        from nsepython import nse_eq

        nse_symbol = self._symbol_nsepython(symbol)
        df = nse_eq(nse_symbol, "ALL", "DAILY")

        if df is None or df.empty:
            raise ValueError(f"No data returned for {symbol}")

        # nsepython returns: Date, Open, High, Low, Close, Volume, ...
        df = df.rename(columns={
            'CH_OPENING_PRICE': 'Open',
            'CH_TRADE_HIGH_PRICE': 'High',
            'CH_TRADE_LOW_PRICE': 'Low',
            'CH_CLOSING_PRICE': 'Close',
            'CH_TOTAL_TRADED_QTY': 'Volume'
        })

        # Keep only needed columns
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

        # Convert date index
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        # Filter date range
        df = df[(df.index >= start) & (df.index <= end)]

        # Ensure numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna()
        return df

    def _fetch_daily_yf(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch daily data via yfinance."""
        import yfinance as yf

        yf_symbol = self._symbol_yfinance(symbol)
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(start=start, end=end, interval="1d")

        if df.empty:
            raise ValueError(f"No data returned for {symbol}")

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)  # Remove timezone
        return df

    def fetch_intraday_15m(self, symbol: str, days: int = 5) -> Optional[pd.DataFrame]:
        """
        Fetch 15-minute intraday data.
        Note: yfinance only provides 15m for last 60 days.
        nsepython doesn't directly support 15m - would need NSE API.
        """
        # For now, use yfinance for 15m (limited to 60 days)
        import yfinance as yf

        yf_symbol = self._symbol_yfinance(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=min(days, 55))  # Max 60 days for 15m

        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=start_date, end=end_date, interval="15m")

            if df.empty:
                return None

            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.index = pd.to_datetime(df.index).tz_convert('Asia/Kolkata').tz_localize(None)
            df = df.sort_index()

            # Filter to market hours only (9:15 - 15:30 IST)
            df = df.between_time('09:15', '15:30')

            return df

        except Exception as e:
            logger.error(f"Error fetching 15m data for {symbol}: {e}")
            return None

    def fetch_multiple_daily(self, symbols: List[str], lookback_days: int = 300) -> Dict[str, pd.DataFrame]:
        """Fetch daily data for multiple symbols."""
        results = {}
        for symbol in symbols:
            df = self.fetch_daily(symbol, lookback_days)
            if df is not None and len(df) > 50:  # Minimum bars for indicators
                results[symbol] = df
            else:
                logger.warning(f"Insufficient data for {symbol}: {len(df) if df is not None else 0} bars")
        return results


# Singleton instance
data_fetcher = DataFetcher(use_nsepython=config.use_nsepython)


def get_data_fetcher() -> DataFetcher:
    return data_fetcher