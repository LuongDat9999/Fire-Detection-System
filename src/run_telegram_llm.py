"""Run Telegram bot for LLM intent testing."""

import logging

from agents.brain import LLMBrain
from chat.telegram_bot import FireTelegramBot
from utils.config import load_config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname).1s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()

    if not config.notifications.telegram_token:
        raise ValueError("TELEGRAM_TOKEN chưa được cấu hình")

    brain = LLMBrain()
    ok, message = brain.check_connection()
    logger.info(message)
    if not ok:
        raise RuntimeError("Không thể kết nối Groq, dừng chạy bot test")

    bot = FireTelegramBot(config.notifications.telegram_token)
    logger.info("Telegram LLM bot is running. Send a message to your bot now.")
    bot.app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
