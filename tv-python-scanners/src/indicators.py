"""
Technical indicators using pandas-ta.
Exact replication of Pine Script calculations.
"""
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential Moving Average."""
    return ta.ema(series, length=length)


def sma(series: pd.Series, length: int) -> pd.Series:
    """Simple Moving Average."""
    return ta.sma(series, length=length)


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Relative Strength Index."""
    return ta.rsi(series, length=length)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range."""
    return ta.atr(high, low, close, length=length)


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Volume Weighted Average Price (session-based)."""
    # pandas-ta vwap expects a DataFrame with OHLCV
    df = pd.DataFrame({'high': high, 'low': low, 'close': close, 'volume': volume})
    return ta.vwap(df['high'], df['low'], df['close'], df['volume'])


def highest(series: pd.Series, length: int) -> pd.Series:
    """Highest value over length periods."""
    return ta.hilo(series, series, length=length)[0]  # Returns (high, low)


def lowest(series: pd.Series, length: int) -> pd.Series:
    """Lowest value over length periods."""
    return ta.hilo(series, series, length=length)[1]


def linreg_slope(series: pd.Series, length: int) -> pd.Series:
    """Linear regression slope (like Pine's linreg)."""
    return ta.linreg(series, length=length, offset=0)


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """True when series1 crosses under series2."""
    return (series1.shift(1) > series2.shift(1)) & (series1 < series2)


def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """True when series1 crosses over series2."""
    return (series1.shift(1) < series2.shift(1)) & (series1 > series2)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On Balance Volume - manual calculation matching Pine."""
    obv_change = volume * np.where(close > close.shift(1), 1,
                                   np.where(close < close.shift(1), -1, 0))
    obv_vals = obv_change.cumsum()
    return obv_vals


def session_vwap(close: pd.Series, high: pd.Series, low: pd.Series,
                 volume: pd.Series, session_reset: pd.Series) -> pd.Series:
    """
    Session-anchored VWAP (resets each day).
    session_reset: Boolean series, True at first bar of each session.
    """
    # Typical price
    typical = (high + low + close) / 3

    # Cumulative typical * volume and cumulative volume per session
    tp_vol = typical * volume
    cum_tp_vol = tp_vol.groupby(session_reset.cumsum()).cumsum()
    cum_vol = volume.groupby(session_reset.cumsum()).cumsum()

    return cum_tp_vol / cum_vol


def is_new_session(index: pd.DatetimeIndex, freq: str = 'D') -> pd.Series:
    """Detect new session (day) boundaries."""
    if freq == 'D':
        # For daily data, each row is a session
        return pd.Series(True, index=index)
    else:
        # For intraday, detect day changes
        dates = index.date
        return pd.Series(dates != pd.Series(dates).shift(1).values, index=index)


def consol_ratio(high: pd.Series, low: pd.Series,
                 lookback_consolid: int, lookback_52w: int) -> pd.Series:
    """Consolidation ratio: 10-day range / 52-week range."""
    range_short = highest(high, lookback_consolid) - lowest(low, lookback_consolid)
    range_long = highest(high, lookback_52w) - lowest(low, lookback_52w)
    return np.where(range_long > 0, range_short / range_long, 0)


def proximity_to_high(close: pd.Series, high: pd.Series, lookback: int) -> pd.Series:
    """Proximity to highest high: (highest - close) / highest."""
    highest_high = highest(high, lookback)
    return (highest_high - close) / highest_high


def trailing_stop_atr(close: pd.Series, high: pd.Series, low: pd.Series,
                      atr_len: int = 14, atr_mult: float = 2.5) -> pd.Series:
    """ATR-based trailing stop (only moves up)."""
    atr_val = atr(high, low, close, atr_len)
    stop = close - atr_val * atr_mult
    # Only move up (max with previous)
    return stop.expanding().max()


# Convenience: compute all indicators for a DataFrame
def compute_all_indicators(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Add all indicator columns to DataFrame."""
    df = df.copy()

    # EMAs
    for name, length in [('ema_fast', params.get('ema_fast', 9)),
                          ('ema_mid', params.get('ema_mid', 21)),
                          ('ema_slow', params.get('ema_slow', 50)),
                          ('ema_trend', params.get('ema_trend', 200))]:
        df[name] = ema(df['Close'], length)

    # RSI
    rsi_len = params.get('rsi_len', 14)
    df['rsi'] = rsi(df['Close'], rsi_len)
    df['rsi_avg'] = sma(df['rsi'], params.get('rsi_avg_len', 20))

    # Volume
    df['vol_avg'] = sma(df['Volume'], params.get('vol_avg_len', 20))

    # OBV
    df['obv'] = obv(df['Close'], df['Volume'])
    df['obv_trend'] = linreg_slope(df['obv'], params.get('lookback_obv', 50))

    # Consolidation
    df['consol_ratio'] = consol_ratio(
        df['High'], df['Low'],
        params.get('lookback_consolid', 10),
        params.get('lookback_52w', 252)
    )

    # Proximity to 52W high
    df['proximity'] = proximity_to_high(
        df['Close'], df['High'], params.get('lookback_52w', 252)
    )

    # Trend continuation
    df['trend_continuation'] = df['Close'] > df['Close'].shift(params.get('lookback_trend', 60))

    # ATR trailing stop
    df['trail_stop'] = trailing_stop_atr(
        df['Close'], df['High'], df['Low'],
        params.get('atr_len', 14), params.get('atr_mult', 2.5)
    )

    # VWAP (session anchored)
    session_reset = is_new_session(df.index)
    df['vwap'] = session_vwap(df['Close'], df['High'], df['Low'], df['Volume'], session_reset)

    return df