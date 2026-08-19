"""
15m Intraday Scalper - Python port of Pine Script.
Exact logic replication for 15-minute timeframe.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.config import config
from src.indicators import (ema, rsi, sma, vwap, highest, lowest,
                             crossunder, session_vwap, is_new_session)
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScalperSignal:
    """Intraday scalper signal result."""
    symbol: str
    timestamp: pd.Timestamp
    close: float
    conditions: Dict[str, bool]
    condition_count: int
    total_conditions: int
    buy_signal: bool
    sell_signal: bool
    key_levels: Dict[str, float]


class IntradayScalper:
    """15m Intraday Scalper matching Pine script logic exactly."""

    def __init__(self, params: Optional[dict] = None):
        self.params = params or config.intraday_scalper

    def evaluate_conditions(self, df: pd.DataFrame) -> Dict[str, bool]:
        """Evaluate all 8 buy conditions + 4 sell conditions on the last row."""
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last

        conditions = {}

        # ========== BUY CONDITIONS ==========

        # 1. Trend filter: price above slow EMA
        conditions['cond1_above_ema_slow'] = last['Close'] > last['ema_slow']

        # 2. Fast EMA above Mid EMA (short-term uptrend)
        conditions['cond2_ema_fast_above_mid'] = last['ema_fast'] > last['ema_mid']

        # 3. Pullback to VWAP or EMA support
        # Pine: useVWAP ? (close <= vwap * 1.002 and close >= emaM * 0.998) : (close >= emaM * 0.998 and close <= emaM * 1.01)
        near_vwap = (last['Close'] <= last['vwap'] * 1.002) and (last['Close'] >= last['ema_mid'] * 0.998)
        near_ema = (last['Close'] >= last['ema_mid'] * 0.998) and (last['Close'] <= last['ema_mid'] * 1.01)
        conditions['cond3_pullback'] = near_vwap if last.get('use_vwap', True) else near_ema

        # 4. RSI in sweet spot
        conditions['cond4_rsi_range'] = (last['rsi'] >= self.params['rsi_low']) and (last['rsi'] <= self.params['rsi_high'])

        # 5. RSI rising
        conditions['cond5_rsi_rising'] = last['rsi'] > prev['rsi']

        # 6. Volume confirmation
        conditions['cond6_volume'] = last['Volume'] >= last['vol_avg'] * 0.8

        # 7. Bullish candle
        conditions['cond7_bullish_candle'] = last['Close'] > last['Open']

        # 8. Not at session high
        conditions['cond8_not_session_high'] = last['Close'] < last['session_high'] * 0.995

        # ========== SELL CONDITIONS ==========

        # 1. Bearish reversal: fast EMA crosses below mid EMA
        conditions['sell1_ema_crossunder'] = (prev['ema_fast'] > prev['ema_mid']) and (last['ema_fast'] < last['ema_mid'])

        # 2. RSI overbought and turning down
        conditions['sell2_rsi_overbought'] = (last['rsi'] > self.params['rsi_high']) and (last['rsi'] < prev['rsi'])

        # 3. Price closes below VWAP
        conditions['sell3_below_vwap'] = last['Close'] < last['vwap'] * 0.998

        # 4. Bearish candle at resistance
        conditions['sell4_bearish_resistance'] = (last['Close'] < last['Open']) and (last['Close'] >= last['session_high'] * 0.99)

        return conditions

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all required indicators for intraday scalper."""
        df = df.copy()
        p = self.params

        # EMAs
        df['ema_fast'] = ema(df['Close'], p['ema_fast'])
        df['ema_mid'] = ema(df['Close'], p['ema_mid'])
        df['ema_slow'] = ema(df['Close'], p['ema_slow'])
        df['ema_trend'] = ema(df['Close'], p['ema_trend'])

        # RSI
        df['rsi'] = rsi(df['Close'], p['rsi_len'])

        # Volume
        df['vol_avg'] = sma(df['Volume'], 20)

        # VWAP (session anchored)
        session_reset = is_new_session(df.index)
        df['vwap'] = session_vwap(df['Close'], df['High'], df['Low'], df['Volume'], session_reset)

        # Session high/low tracking
        df['session_high'] = df.groupby(session_reset.cumsum())['High'].cummax()
        df['session_low'] = df.groupby(session_reset.cumsum())['Low'].cummin()

        return df

    def scan_symbol(self, symbol: str, df: pd.DataFrame) -> Optional[ScalperSignal]:
        """Run scan on a single symbol's 15m DataFrame."""
        if df is None or len(df) < 200:  # Need enough for EMA 200
            return None

        # Compute indicators
        df = self.compute_indicators(df)

        conditions = self.evaluate_conditions(df)
        condition_count = sum(v for k, v in conditions.items() if k.startswith('cond'))
        total_buy_conditions = sum(1 for k in conditions if k.startswith('cond'))

        buy_signal = all(v for k, v in conditions.items() if k.startswith('cond'))
        sell_signal = any(v for k, v in conditions.items() if k.startswith('sell'))

        key_levels = {
            'close': float(df.iloc[-1]['Close']),
            'ema_9': float(df.iloc[-1]['ema_fast']),
            'ema_21': float(df.iloc[-1]['ema_mid']),
            'ema_50': float(df.iloc[-1]['ema_slow']),
            'ema_200': float(df.iloc[-1]['ema_trend']),
            'vwap': float(df.iloc[-1]['vwap']),
            'rsi': float(df.iloc[-1]['rsi']),
            'session_high': float(df.iloc[-1]['session_high']),
            'session_low': float(df.iloc[-1]['session_low']),
            'target': float(df.iloc[-1]['Close'] * (1 + p['target_pct'])),
            'stop': float(df.iloc[-1]['Close'] * (1 - p['stop_pct'])),
        }

        return ScalperSignal(
            symbol=symbol,
            timestamp=df.index[-1],
            close=float(df.iloc[-1]['Close']),
            conditions=conditions,
            condition_count=condition_count,
            total_conditions=total_buy_conditions,
            buy_signal=buy_signal,
            sell_signal=sell_signal,
            key_levels=key_levels
        )

    def format_signal(self, signal: ScalperSignal) -> str:
        """Format scalper signal for alert."""
        lines = [
            f"⚡ INTRADAY SCALPER: {signal.symbol}",
            f"Price: ₹{signal.close:.2f} | {signal.condition_count}/{signal.total_conditions} buy conditions",
            "",
            "🟢 BUY CONDITIONS:",
            f"  {'✅' if signal.conditions.get('cond1_above_ema_slow') else '❌'} Price > EMA 50",
            f"  {'✅' if signal.conditions.get('cond2_ema_fast_above_mid') else '❌'} EMA 9 > EMA 21",
            f"  {'✅' if signal.conditions.get('cond3_pullback') else '❌'} Near VWAP/EMA21",
            f"  {'✅' if signal.conditions.get('cond4_rsi_range') else '❌'} RSI 45-68",
            f"  {'✅' if signal.conditions.get('cond5_rsi_rising') else '❌'} RSI Rising",
            f"  {'✅' if signal.conditions.get('cond6_volume') else '❌'} Volume OK",
            f"  {'✅' if signal.conditions.get('cond7_bullish_candle') else '❌'} Bullish Candle",
            f"  {'✅' if signal.conditions.get('cond8_not_session_high') else '❌'} Not at High",
            "",
            "🔴 SELL CONDITIONS:",
            f"  {'⚠️' if signal.conditions.get('sell1_ema_crossunder') else '✅'} EMA 9 x EMA 21",
            f"  {'⚠️' if signal.conditions.get('sell2_rsi_overbought') else '✅'} RSI Overbought+Down",
            f"  {'⚠️' if signal.conditions.get('sell3_below_vwap') else '✅'} Below VWAP",
            f"  {'⚠️' if signal.conditions.get('sell4_bearish_resistance') else '✅'} Bearish at Resist",
        ]

        if signal.buy_signal:
            lines.insert(1, "✅ **BUY SIGNAL ACTIVE**")
        elif signal.sell_signal:
            lines.insert(1, "🔴 **SELL SIGNAL ACTIVE**")
        else:
            lines.insert(1, "⏳ No signal")

        lines.extend([
            "",
            "📈 LEVELS:",
            f"  VWAP: ₹{signal.key_levels['vwap']:.2f}",
            f"  EMA 9/21/50: {signal.key_levels['ema_9']:.1f} / {signal.key_levels['ema_21']:.1f} / {signal.key_levels['ema_50']:.1f}",
            f"  RSI: {signal.key_levels['rsi']:.1f}",
            f"  Session H/L: {signal.key_levels['session_high']:.1f} / {signal.key_levels['session_low']:.1f}",
            f"  Target (+1.5%): ₹{signal.key_levels['target']:.2f}",
            f"  Stop (-0.8%): ₹{signal.key_levels['stop']:.2f}",
        ])

        return "\n".join(lines)


def run_intraday_scan(data_dict: Dict[str, pd.DataFrame], params: Optional[dict] = None) -> List[ScalperSignal]:
    """Run intraday scan on multiple symbols."""
    scalper = IntradayScalper(params)
    signals = []

    for symbol, df in data_dict.items():
        try:
            signal = scalper.scan_symbol(symbol, df)
            if signal:
                signals.append(signal)
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")

    # Sort: buy signals first, then by condition count
    signals.sort(key=lambda x: (not x.buy_signal, -x.condition_count))
    return signals