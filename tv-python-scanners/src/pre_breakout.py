"""
Pre-Breakout AI Scanner - Python port of Pine Script.
Exact logic replication for daily timeframe scanning.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from src.config import config
from src.indicators import compute_all_indicators
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of pre-breakout scan for one symbol."""
    symbol: str
    timestamp: pd.Timestamp
    close: float
    conditions: Dict[str, bool]
    condition_count: int
    total_conditions: int
    passed: bool
    key_levels: Dict[str, float]
    metadata: Dict[str, any]


class PreBreakoutScanner:
    """Pre-Breakout AI Scanner matching Pine script logic exactly."""

    def __init__(self, params: Optional[dict] = None):
        self.params = params or config.pre_breakout

    def evaluate_conditions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Evaluate all 12 buy conditions on the last row."""
        # Compute indicators if not present
        if 'ema_fast' not in df.columns:
            df = compute_all_indicators(df, self.params)

        # Get last row
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last

        conditions = {}

        # 1. Price Proximity: Close within proximity_pct of 52-week High
        conditions['cond1_proximity'] = last['proximity'] <= self.params['proximity_pct']

        # 2. Consolidation: 10-day range is tight vs 52-week range
        conditions['cond2_consolidation'] = last['consol_ratio'] <= self.params['consol_threshold']

        # 3. Trend Alignment: 20 EMA > 50 EMA > 200 EMA
        conditions['cond3_ema_alignment'] = (last['ema_fast'] > last['ema_mid']) and (last['ema_mid'] > last['ema_slow'])

        # 4. RSI Sweet Spot: RSI between rsi_low and rsi_high
        conditions['cond4_rsi_range'] = (last['rsi'] >= self.params['rsi_low']) and (last['rsi'] <= self.params['rsi_high'])

        # 5. RSI 20-day Average > rsi_avg_min
        conditions['cond5_rsi_avg'] = last['rsi_avg'] > self.params['rsi_avg_min']

        # 6. Momentum Rising: Current RSI > RSI 5 bars ago
        rsi_5_ago = df['rsi'].iloc[-6] if len(df) >= 6 else last['rsi']
        conditions['cond6_rsi_momentum'] = last['rsi'] > rsi_5_ago

        # 7. Volume Compression: Current volume < 20-day volume average
        conditions['cond7_volume_compressed'] = last['Volume'] < last['vol_avg']

        # 8. Accumulation (OBV): OBV trending upward (linreg slope > 0)
        conditions['cond8_obv_trend'] = last['obv_trend'] > 0

        # 9. Trend Continuation: Price > Price 60 days ago
        conditions['cond9_trend_continuation'] = last['trend_continuation']

        # 10. Price above 200 EMA (long-term uptrend)
        conditions['cond10_above_ema200'] = last['Close'] > last['ema_slow']

        # 11. Price above 50 EMA (medium-term uptrend)
        conditions['cond11_above_ema50'] = last['Close'] > last['ema_mid']

        # 12. RSI not overbought (< 70 for safety)
        conditions['cond12_rsi_not_overbought'] = last['rsi'] < 70

        return conditions

    def get_key_levels(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract key price levels for the scan result."""
        last = df.iloc[-1]
        return {
            'close': float(last['Close']),
            'high_52w': float(ta.highest(df['High'], self.params['lookback_52w']).iloc[-1]),
            'ema_20': float(last['ema_fast']),
            'ema_50': float(last['ema_mid']),
            'ema_200': float(last['ema_slow']),
            'rsi': float(last['rsi']),
            'rsi_avg': float(last['rsi_avg']),
            'consol_ratio_pct': float(last['consol_ratio'] * 100),
            'proximity_pct': float(last['proximity'] * 100),
            'trail_stop': float(last['trail_stop']) if not pd.isna(last['trail_stop']) else None,
            'vwap': float(last['vwap']) if not pd.isna(last['vwap']) else None,
        }

    def scan_symbol(self, symbol: str, df: pd.DataFrame) -> ScanResult:
        """Run scan on a single symbol's DataFrame."""
        if df is None or len(df) < max(self.params['lookback_52w'], 200) + 10:
            return None

        conditions = self.evaluate_conditions(df)
        condition_count = sum(conditions.values())
        total_conditions = len(conditions)
        passed = condition_count >= config.min_conditions_pre_breakout

        key_levels = self.get_key_levels(df)

        return ScanResult(
            symbol=symbol,
            timestamp=df.index[-1],
            close=float(df.iloc[-1]['Close']),
            conditions=conditions,
            condition_count=condition_count,
            total_conditions=total_conditions,
            passed=passed,
            key_levels=key_levels,
            metadata={
                'params_used': self.params,
                'data_bars': len(df)
            }
        )

    def scan_universe(self, data_dict: Dict[str, pd.DataFrame]) -> List[ScanResult]:
        """Scan multiple symbols."""
        results = []
        for symbol, df in data_dict.items():
            try:
                result = self.scan_symbol(symbol, df)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")

        # Sort by condition count (best first)
        results.sort(key=lambda x: x.condition_count, reverse=True)
        return results

    def format_result(self, result: ScanResult) -> str:
        """Format scan result for display/alert."""
        cond_status = []
        cond_names = {
            'cond1_proximity': 'Proximity ≤25%',
            'cond2_consolidation': 'Consolidation ≤15%',
            'cond3_ema_alignment': 'EMA 20>50>200',
            'cond4_rsi_range': 'RSI 40-65',
            'cond5_rsi_avg': 'RSI Avg >50',
            'cond6_rsi_momentum': 'RSI Rising',
            'cond7_volume_compressed': 'Vol Compressed',
            'cond8_obv_trend': 'OBV Up',
            'cond9_trend_continuation': 'Trend 60d Up',
            'cond10_above_ema200': '>EMA200',
            'cond11_above_ema50': '>EMA50',
            'cond12_rsi_not_overbought': 'RSI <70',
        }

        for key, name in cond_names.items():
            status = "✅" if result.conditions.get(key, False) else "❌"
            cond_status.append(f"{status} {name}")

        lines = [
            f"📊 PRE-BREAKOUT SCAN: {result.symbol}",
            f"Price: ₹{result.close:.2f} | {result.condition_count}/{result.total_conditions} conditions",
            "",
            *cond_status,
            "",
            "📈 KEY LEVELS:",
            f"  52W High: ₹{result.key_levels.get('high_52w', 0):.2f}",
            f"  Proximity: {result.key_levels.get('proximity_pct', 0):.1f}%",
            f"  Consolidation: {result.key_levels.get('consol_ratio_pct', 0):.1f}%",
            f"  EMA 20/50/200: {result.key_levels.get('ema_20', 0):.1f} / {result.key_levels.get('ema_50', 0):.1f} / {result.key_levels.get('ema_200', 0):.1f}",
            f"  RSI: {result.key_levels.get('rsi', 0):.1f} (Avg: {result.key_levels.get('rsi_avg', 0):.1f})",
        ]

        if result.key_levels.get('trail_stop'):
            lines.append(f"  Trail Stop: ₹{result.key_levels['trail_stop']:.2f}")

        if result.passed:
            lines.insert(1, "✅ **QUALIFIES FOR ALERT**")
        else:
            lines.insert(1, f"⚠️  Below threshold ({config.min_conditions_pre_breakout} needed)")

        return "\n".join(lines)


# Convenience function
def run_pre_breakout_scan(data_dict: Dict[str, pd.DataFrame], params: Optional[dict] = None) -> List[ScanResult]:
    scanner = PreBreakoutScanner(params)
    return scanner.scan_universe(data_dict)