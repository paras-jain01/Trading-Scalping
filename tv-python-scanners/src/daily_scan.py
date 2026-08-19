#!/usr/bin/env python3
"""
Daily Pre-Breakout Scanner - Main entry point for GitHub Actions.
Runs post-market scan and sends results to Telegram.
"""
import sys
import os
from datetime import datetime
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import config, validate_config
from src.data import get_data_fetcher
from src.pre_breakout import run_pre_breakout_scan, ScanResult
from src.telegram import get_bot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_results_to_file(results: list, filename: str):
    """Save results to a text file for artifact upload."""
    with open(filename, 'w') as f:
        f.write(f"DAILY PRE-BREAKOUT SCAN RESULTS\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Universe: {len(config.scan_universe)} symbols\n")
        f.write(f"Min conditions: {config.min_conditions_pre_breakout}/12\n")
        f.write("=" * 60 + "\n\n")

        for r in results:
            scanner = r.__class__.__module__.split('.')[-1]  # Hack to get scanner
            # Just use the format method
            from src.pre_breakout import PreBreakoutScanner
            pb_scanner = PreBreakoutScanner()
            f.write(pb_scanner.format_result(r))
            f.write("\n\n" + "=" * 60 + "\n\n")


def main():
    """Main entry point for daily scan."""
    logger.info("Starting daily pre-breakout scan...")

    # Validate config
    if not validate_config():
        logger.error("Configuration validation failed. Check secrets.")
        sys.exit(1)

    # Fetch data for all symbols
    logger.info(f"Fetching data for {len(config.scan_universe)} symbols...")
    fetcher = get_data_fetcher()
    data = fetcher.fetch_multiple_daily(config.scan_universe, config.lookback_days)

    logger.info(f"Successfully fetched data for {len(data)} symbols")

    if not data:
        logger.error("No data fetched for any symbol")
        get_bot().send_message("❌ Daily Scan Failed: No data fetched")
        sys.exit(1)

    # Run scan
    logger.info("Running pre-breakout scanner...")
    results = run_pre_breakout_scan(data)

    # Filter qualified
    qualified = [r for r in results if r.passed]
    close_calls = [r for r in results if not r.passed and r.condition_count >= 9]

    logger.info(f"Scan complete: {len(qualified)} qualified, {len(close_calls)} close calls")

    # Prepare messages
    bot = get_bot()

    # Summary message
    summary = f"📊 <b>Daily Pre-Breakout Scan - {datetime.now().strftime('%d %b %Y')}</b>\n"
    summary += f"Universe: {len(config.scan_universe)} | Scanned: {len(data)}\n"
    summary += f"✅ Qualified (≥{config.min_conditions_pre_breakout}/12): <b>{len(qualified)}</b>\n"
    summary += f"⚠️ Close (9-10/12): <b>{len(close_calls)}</b>\n"

    if qualified:
        summary += "\n<b>QUALIFIED:</b>\n"
        for r in qualified:
            summary += f"  • {r.symbol}: {r.condition_count}/12 @ ₹{r.close:.2f}\n"
    else:
        summary += "\n❌ No stocks qualified today."

    if close_calls:
        summary += "\n<b>WATCHLIST (close):</b>\n"
        for r in close_calls:
            summary += f"  • {r.symbol}: {r.condition_count}/12 @ ₹{r.close:.2f}\n"

    # Send summary
    bot.send_message(summary)

    # Send detailed results for qualified (max 3 per message)
    if qualified:
        detailed = [PreBreakoutScanner().format_result(r) for r in qualified]
        bot.send_scan_results(detailed, "📊 QUALIFIED STOCKS - DETAILS")

    if close_calls:
        detailed_close = [PreBreakoutScanner().format_result(r) for r in close_calls]
        bot.send_scan_results(detailed_close, "⚠️ WATCHLIST - DETAILS")

    # Save results for artifact
    timestamp = datetime.now().strftime('%Y%m%d')
    save_results_to_file(results, f"scan_results_{timestamp}.txt")

    logger.info("Daily scan completed successfully")


if __name__ == "__main__":
    main()