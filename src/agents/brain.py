import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

current_file = Path(__file__).resolve()
candidate_paths = [
    current_file.parents[2] / ".env",  # fire-detection-system/.env
    current_file.parents[1] / ".env",  # src/.env fallback
]
for env_path in candidate_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break


class Intent(str, Enum):
    MUTE = "MUTE"
    SHOW_CAMERA = "SHOW_CAMERA"
    STATUS = "STATUS"
    MONITORING_INTENSELY = "MONITORING_INTENSELY"
    EMERGENCY = "EMERGENCY"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentResult:
    intent: Intent
    confidence: float = 0.0
    raw_output: str = ""


class LLMBrain:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY không tồn tại trong .env")

        self.client = Groq(api_key=self.api_key)

    def check_connection(self):
        """Kiểm tra kết nối bằng một prompt ngắn."""
        try:
            self.client.chat.completions.create(
                messages=[{"role": "user", "content": "ping"}],
                model=self.model_name,
                max_tokens=5,
            )
            return True, "Kết nối Groq thành công!"
        except Exception as e:
            return False, f"Lỗi kết nối Groq: {str(e)}"

    def classify_intent(self, user_text: str) -> IntentResult:
        """Sử dụng Groq để map tin nhắn thành đúng 1 intent."""
        fallback = self._keyword_fallback(user_text)

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là intent classifier cho hệ thống báo cháy. "
                            "Chỉ trả về DUY NHẤT 1 nhãn trong danh sách sau, "
                            "không thêm chữ nào khác: "
                            "MUTE, SHOW_CAMERA, STATUS, MONITORING_INTENSELY, EMERGENCY, UNKNOWN. "
                            "Quy tắc: \n"
                            "- Tắt báo động, im lặng, mute => MUTE\n"
                            "- Xem camera, gửi ảnh hiện tại, snapshot => SHOW_CAMERA\n"
                            "- Kiểm tra hệ thống, trạng thái, tình hình hiện tại => STATUS\n"
                            "- Theo dõi kỹ hơn, tăng cường giám sát => MONITORING_INTENSELY\n"
                            "- Cứu hỏa ngay, báo khẩn cấp, emergency => EMERGENCY\n"
                            "- Không rõ ý định => UNKNOWN"
                        ),
                    },
                    {"role": "user", "content": user_text},
                ],
                model=self.model_name,
                temperature=0,
                max_tokens=10,
            )

            raw = (chat_completion.choices[0].message.content or "").strip().upper()
            intent = self._normalize_intent(raw)

            if intent == Intent.UNKNOWN:
                return IntentResult(intent=fallback, confidence=0.45, raw_output=raw)

            return IntentResult(intent=intent, confidence=0.90, raw_output=raw)
        except Exception as e:
            return IntentResult(intent=fallback, confidence=0.30, raw_output=f"ERROR: {str(e)}")

    def _normalize_intent(self, raw_output: str) -> Intent:
        first_line = raw_output.splitlines()[0] if raw_output else ""
        token = re.sub(r"[^A-Z_]", "", first_line)
        try:
            return Intent(token)
        except ValueError:
            return Intent.UNKNOWN

    def _keyword_fallback(self, user_text: str) -> Intent:
        text = user_text.lower().strip()

        if any(
            k in text
            for k in [
                "tắt",
                "tat",
                "im lặng",
                "im lang",
                "mute",
                "silence",
                "dừng báo động",
                "dung bao dong",
                "tat bao dong",
            ]
        ):
            return Intent.MUTE
        if any(k in text for k in ["camera", "ảnh", "hình", "snapshot", "xem"]):
            return Intent.SHOW_CAMERA
        if any(k in text for k in ["trạng thái", "status", "tình hình", "kiểm tra"]):
            return Intent.STATUS
        if any(k in text for k in ["tăng cường", "theo dõi", "giám sát kỹ", "monitor"]):
            return Intent.MONITORING_INTENSELY
        if any(k in text for k in ["khẩn cấp", "emergency", "cứu hỏa", "gọi cứu hỏa"]):
            return Intent.EMERGENCY
        return Intent.UNKNOWN