"""
Telegram bot sender for scan alerts.
"""
import requests
import logging
from typing import Optional, List
from src.config import config

logger = logging.getLogger(__name__)


class TelegramBot:
    """Simple Telegram bot for sending messages."""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or config.telegram_bot_token
        self.chat_id = chat_id or config.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str, chat_id: str = None, parse_mode: str = "HTML") -> bool:
        """Send a message to Telegram."""
        if not self.token or not self.chat_id:
            logger.error("Telegram token or chat_id not configured")
            return False

        target_chat = chat_id or self.chat_id
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("ok", False)
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_scan_results(self, results: List, title: str, max_per_message: int = 3) -> bool:
        """Send multiple scan results, batching if needed."""
        if not results:
            return self.send_message(f"{title}\n\nNo results found.")

        # Split into chunks
        for i in range(0, len(results), max_per_message):
            chunk = results[i:i + max_per_message]
            message = f"{title} ({i+1}-{i+len(chunk)} of {len(results)})\n\n"
            message += "\n\n---\n\n".join([r for r in chunk])

            if len(message) > 4000:  # Telegram limit
                message = message[:3997] + "..."

            if not self.send_message(message):
                return False

        return True

    def test(self) -> bool:
        """Test the bot connection."""
        return self.send_message("🤖 Bot test - Connection successful!")


# Singleton
_bot = None


def get_bot() -> TelegramBot:
    global _bot
    if _bot is None:
        _bot = TelegramBot()
    return _bot


def send_telegram(text: str) -> bool:
    """Convenience function to send a message."""
    return get_bot().send_message(text)