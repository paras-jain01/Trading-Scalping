#!/usr/bin/env python3
"""
Intraday Scalper Scan - Runs during market hours (9:15-15:30 IST).
Deployed as a background service on Render/Railway free tier.
Polls every 15 minutes and sends BUY/SELL alerts.
"""
import sys
import os
import time
import signal
from datetime import datetime, time as dt_time
from typing import Dict
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import config, validate_config
from src.data import get_data_fetcher
from src.intraday_scalper import run_intraday_scan, ScalperSignal
from src.telegram import get_bot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntradayScanner:
    """Runs intraday scans at 15-minute intervals during market hours."""

    def __init__(self):
        self.running = False
        self.last_signals = {}  # Track last signal state per symbol to avoid duplicates
        self.fetcher = get_data_fetcher()
        self.bot = get_bot()

    def is_market_hours(self) -> bool:
        """Check if current time is within market hours (IST)."""
        now = datetime.now()
        ist_now = now  # Assuming system timezone is IST or we handle it

        # Simple check - in production use pytz
        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)
        current_time = ist_now.time()

        # Also check weekday (Mon-Fri)
        if ist_now.weekday() >= 5:  # Sat=5, Sun=6
            return False

        return market_open <= current_time <= market_close

    def should_scan(self) -> bool:
        """Check if we should run a scan (every 15 minutes)."""
        now = datetime.now()
        return now.minute % 15 == 0 and now.second < 30

    def scan_once(self) -> Dict[str, ScalperSignal]:
        """Run one scan cycle."""
        logger.info("Running intraday scan...")

        # Fetch 15m data for universe (limited to liquid names for speed)
        # Use subset for intraday to avoid rate limits
        intraday_universe = config.scan_universe[:15]  # Top 15 most liquid

        data = {}
        for symbol in intraday_universe:
            try:
                df = self.fetcher.fetch_intraday_15m(symbol, days=3)
                if df is not None and len(df) >= 200:
                    data[symbol] = df
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")

        if not data:
            logger.warning("No intraday data fetched")
            return {}

        # Run scan
        signals = run_intraday_scan(data)

        # Filter for new/changed signals only
        new_signals = {}
        for signal in signals:
            key = f"{signal.symbol}_{'BUY' if signal.buy_signal else 'SELL' if signal.sell_signal else 'NONE'}"

            if key not in self.last_signals or self.last_signals[key] != signal.timestamp:
                new_signals[signal.symbol] = signal
                self.last_signals[key] = signal.timestamp

        return new_signals

    def send_alerts(self, signals: Dict[str, ScalperSignal]):
        """Send Telegram alerts for new signals."""
        if not signals:
            return

        from src.intraday_scalper import IntradayScalper
        scalper = IntradayScalper()

        for symbol, signal in signals.items():
            if signal.buy_signal:
                message = f"🟢 <b>INTRADAY BUY ALERT</b>\n\n{scalper.format_signal(signal)}"
                self.bot.send_message(message)
                logger.info(f"Sent BUY alert for {symbol}")

            elif signal.sell_signal:
                message = f"🔴 <b>INTRADAY SELL ALERT</b>\n\n{scalper.format_signal(signal)}"
                self.bot.send_message(message)
                logger.info(f"Sent SELL alert for {symbol}")

    def run(self):
        """Main loop - runs until stopped."""
        self.running = True
        logger.info("Intraday scanner started. Press Ctrl+C to stop.")

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        while self.running:
            try:
                if self.is_market_hours() and self.should_scan():
                    signals = self.scan_once()
                    if signals:
                        self.send_alerts(signals)
                    else:
                        logger.debug("No new signals this cycle")

                # Sleep until next minute
                time.sleep(60)

            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
                time.sleep(60)

        logger.info("Intraday scanner stopped.")

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


def main():
    """Entry point for Render/Railway service."""
    if not validate_config():
        logger.error("Configuration validation failed")
        sys.exit(1)

    scanner = IntradayScanner()
    scanner.run()


if __name__ == "__main__":
    main()