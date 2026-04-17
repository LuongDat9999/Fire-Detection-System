"""Configuration management for the simplified fire detection system."""

import os
from pathlib import Path
from dataclasses import dataclass, field

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    current_file = Path(__file__).resolve()
    candidate_paths = [
        current_file.parents[2] / ".env",  # fire-detection-system/.env
        current_file.parents[1] / ".env",  # src/.env (legacy fallback)
    ]
    for env_path in candidate_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # python-dotenv not installed, use system env vars


@dataclass
class InferenceConfig:
    """Inference configuration (PyTorch YOLO)."""
    model_path: str = os.getenv("MODEL_PATH", "models/best_v3.pt")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
    iou_threshold: float = float(os.getenv("IOU_THRESHOLD", "0.45"))


@dataclass
class NotificationConfig:
    """Telegram notification configuration."""
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    send_frames: bool = True


@dataclass
class SystemConfig:
    """Main system configuration."""
    debug: bool = False
    video_source: str = os.getenv("VIDEO_SOURCE", "data/videos/warehouse.mp4")
    display_fps: bool = True

    inference: InferenceConfig = field(default_factory=InferenceConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)


def load_config() -> SystemConfig:
    """Load configuration from environment and defaults."""
    return SystemConfig()
