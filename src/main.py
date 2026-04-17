"""Main entry point for the simplified fire detection system."""

import argparse
import asyncio
import logging
import platform
import threading

import cv2
import numpy as np

from core.system import FireDetectionSystem
from core.state_manager import StateManager
from chat.telegram_bot import FireTelegramBot
from agents.brain import LLMBrain
from utils.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname).1s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("fire_detection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MockDetector:
    """Small mock detector used for LLM debug without opening camera/video source."""

    def __init__(self) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            frame,
            "LLM DEBUG FRAME",
            (140, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        self.current_frame = frame


def create_state_manager() -> StateManager:
    """Build a shared runtime state manager with config-driven fire confirmation windows."""
    config = load_config()
    return StateManager(
        fire_confirmation_seconds=config.fire_confirmation_seconds,
        fire_absence_reset_seconds=config.fire_absence_reset_seconds,
        trend_threshold_ratio=config.trend_threshold_ratio,
    )


def apply_cli_runtime_options(system: FireDetectionSystem, args: argparse.Namespace) -> None:
    """Apply CLI overrides consistently for every runtime mode."""
    if args.source:
        system.config.video_source = args.source
        logger.info("CLI source: %s", args.source)

    if args.no_display:
        system.show_display = False
        logger.info("Display off")


def create_vision_system(
    args: argparse.Namespace,
    state_manager: StateManager | None = None,
    use_builtin_notifier: bool = True,
) -> FireDetectionSystem:
    """Create and configure the vision system from CLI/runtime dependencies."""
    system = FireDetectionSystem(state_manager=state_manager, use_builtin_notifier=use_builtin_notifier)
    apply_cli_runtime_options(system, args)
    return system


def create_telegram_llm_bot(detector=None, state_manager: StateManager | None = None) -> FireTelegramBot | None:
    """Create Telegram LLM bot instance when env/config are valid."""
    config = load_config()
    token = config.notifications.telegram_token

    if not token:
        logger.warning("Telegram LLM bot skipped: TELEGRAM_TOKEN is missing")
        return None

    try:
        brain = LLMBrain()
        ok, message = brain.check_connection()
        logger.info("LLM check: %s", message)
        if not ok:
            logger.warning("Telegram LLM bot skipped: Groq connection failed")
            return None

        return FireTelegramBot(token, detector=detector, state_manager=state_manager)
    except Exception as e:
        logger.exception("Telegram LLM bot init failed: %s", e)
        return None


def run_vision_module(system: FireDetectionSystem) -> None:
    """Blocking vision loop entrypoint for a dedicated thread."""
    try:
        logger.info("[VISION] Start detector loop")
        system.run()
    except Exception as e:
        logger.exception("[VISION] Runtime error: %s", e)


def start_telegram_bot_in_background(bot: FireTelegramBot) -> asyncio.AbstractEventLoop | None:
    """Run Telegram bot in a daemon thread and return its running event loop."""
    ready = threading.Event()
    loop_holder: dict[str, asyncio.AbstractEventLoop] = {}

    def _thread_entry() -> None:
        async def _runner() -> None:
            loop_holder["loop"] = asyncio.get_running_loop()
            ready.set()

            async with bot.app:
                await bot.app.initialize()
                await bot.app.start()
                await bot.app.updater.start_polling(drop_pending_updates=True)
                try:
                    while True:
                        await asyncio.sleep(1)
                finally:
                    await bot.app.updater.stop()
                    await bot.app.stop()

        try:
            asyncio.run(_runner())
        except Exception as e:
            logger.exception("[BOT] Background runtime error: %s", e)

    threading.Thread(target=_thread_entry, name="telegram-llm-bot", daemon=True).start()
    if not ready.wait(timeout=10):
        logger.error("[BOT] Background bot loop startup timed out")
        return None

    return loop_holder.get("loop")


async def run_bot_with_vision_thread(args: argparse.Namespace) -> None:
    """Run Telegram bot in main asyncio loop and vision in background thread."""
    config = load_config()
    chat_id = config.notifications.telegram_chat_id
    state_manager = create_state_manager()

    system = create_vision_system(args, state_manager=state_manager, use_builtin_notifier=False)

    bot = create_telegram_llm_bot(detector=system.detector, state_manager=state_manager)

    if bot is None:
        logger.warning("Fallback to detector-only mode")
        system = create_vision_system(args)
        system.run()
        return

    # On macOS, OpenCV display is most stable on main thread.
    if platform.system() == "Darwin" and not args.no_display:
        bot_loop = start_telegram_bot_in_background(bot)
        if bot_loop is None:
            logger.warning("Fallback to detector-only mode (background bot failed)")
            system.use_builtin_notifier = True
            system.run()
            return

        def on_fire_alert(frame, message) -> None:
            future = asyncio.run_coroutine_threadsafe(
                bot.send_fire_alert(chat_id, frame, message),
                bot_loop,
            )

            def _on_done(done_future):
                exc = done_future.exception()
                if exc:
                    logger.warning("Async Telegram alert failed: %s", exc)

            future.add_done_callback(_on_done)

        system.alert_callback = on_fire_alert

        logger.info("[VISION] macOS display mode: detector on main thread")
        try:
            system.run()
        finally:
            logger.info("[BOT] Background bot will stop with process exit")
        return

    loop = asyncio.get_running_loop()

    def on_fire_alert(frame, message) -> None:
        future = asyncio.run_coroutine_threadsafe(
            bot.send_fire_alert(chat_id, frame, message),
            loop,
        )

        def _on_done(done_future):
            exc = done_future.exception()
            if exc:
                logger.warning("Async Telegram alert failed: %s", exc)

        future.add_done_callback(_on_done)

    system.alert_callback = on_fire_alert

    vision_thread = threading.Thread(
        target=run_vision_module,
        args=(system,),
        name="vision-detector",
        daemon=True,
    )
    vision_thread.start()

    logger.info("[BOT] Telegram bot ready")
    async with bot.app:
        await bot.app.initialize()
        await bot.app.start()
        await bot.app.updater.start_polling(drop_pending_updates=True)
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            await bot.app.updater.stop()
            await bot.app.stop()


def run_llm_debug_mode() -> None:
    """Run Telegram LLM bot without camera by wiring mock runtime dependencies."""
    config = load_config()
    if not config.notifications.telegram_token:
        raise ValueError("TELEGRAM_TOKEN is missing")

    state_manager = create_state_manager()
    mock_detector = MockDetector()
    bot = create_telegram_llm_bot(
        detector=mock_detector,
        state_manager=state_manager,
    )

    if bot is None:
        raise RuntimeError("Telegram LLM bot init failed in debug mode")

    logger.info("[BOT] LLM debug mode is running (no camera)")
    bot.app.run_polling(drop_pending_updates=True)


def main():
    parser = argparse.ArgumentParser(description="Fire Detection System")
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Video source (file path or camera index, e.g., 0 for webcam)"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run without displaying video window"
    )
    parser.add_argument(
        "--with-telegram-llm",
        action="store_true",
        help="Run Telegram bot (LLM intent replies) alongside fire detection"
    )
    parser.add_argument(
        "--llm-debug",
        action="store_true",
        help="Run only Telegram LLM bot in debug mode using mock runtime (no camera)"
    )

    args = parser.parse_args()

    if args.llm_debug:
        try:
            run_llm_debug_mode()
        except KeyboardInterrupt:
            logger.info("Interrupted")
        return

    if args.with_telegram_llm:
        try:
            asyncio.run(run_bot_with_vision_thread(args))
        except KeyboardInterrupt:
            logger.info("Interrupted")
        return

    system = create_vision_system(args, state_manager=create_state_manager())
    system.run()

if __name__ == "__main__":
    main()
    