"""Notification utilities for sending Telegram fire alerts."""

import cv2
import logging
import requests
import numpy as np

logger = logging.getLogger(__name__)


class Notifier:
    """Handle Telegram notifications."""

    def __init__(self, telegram_token: str, telegram_chat_id: str):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.api_url = f"https://api.telegram.org/bot{telegram_token}"
        self._missing_credentials_logged = False

    def send_alert(self, frame: np.ndarray, message: str) -> bool:
        """Send fire alert to Telegram with current frame."""
        if not self.telegram_token or not self.telegram_chat_id:
            if not self._missing_credentials_logged:
                logger.warning("Telegram not configured")
                self._missing_credentials_logged = True
            return False

        try:
            ok, jpeg_frame = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                logger.error("Frame encode failed")
                return False

            files = {"photo": ("fire_detection.jpg", jpeg_frame.tobytes(), "image/jpeg")}
            data = {
                "chat_id": self.telegram_chat_id,
                "caption": message,
                "parse_mode": "HTML",
            }

            response = requests.post(f"{self.api_url}/sendPhoto", files=files, data=data)
            if response.status_code == 200:
                return True

            logger.error(f"Telegram API error: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
