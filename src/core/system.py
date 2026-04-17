"""Runtime coordinator for the fire detection pipeline."""

import logging
import sys
import time
from datetime import datetime
from typing import Optional, Union, Callable

import cv2

from core.detector import FireDetector
from core.state_manager import StateManager
from utils import FrameDrawer, Notifier
from utils.config import load_config

logger = logging.getLogger(__name__)


class FireDetectionSystem:
    """Main fire detection system coordinator."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        alert_callback: Optional[Callable] = None,
        use_builtin_notifier: bool = True,
        state_manager: Optional[StateManager] = None,
    ):
        del config_path  # reserved for future config-file support
        self.config = load_config()
        self.alert_callback = alert_callback
        self.use_builtin_notifier = use_builtin_notifier
        self.state_manager = state_manager or StateManager()

        self._init_detector()
        self._init_notifier()
        self._init_drawer()

        self.alert_cooldown = 10.0
        self.last_alert_time = 0.0
        self.show_display = True
        self.show_fps = self.config.display_fps
        self.prev_has_fire = False
        self.last_fire_log_time = 0.0
        self.fire_log_interval = 2.0

        self.fps_timer = time.time()
        self.fps_counter = 0

        logger.info(
            "System ready | model=%s | source=%s",
            self.config.inference.model_path,
            self.config.video_source,
        )

    def _init_detector(self) -> None:
        try:
            self.detector = FireDetector(model_path=self.config.inference.model_path)
        except Exception as e:
            logger.error("Init detector failed: %s", e)
            sys.exit(1)

    def _init_notifier(self) -> None:
        self.notifier = Notifier(
            telegram_token=self.config.notifications.telegram_token,
            telegram_chat_id=self.config.notifications.telegram_chat_id,
        )
        if self.config.notifications.telegram_token and self.config.notifications.telegram_chat_id:
            logger.info("Telegram notifier configured")
        else:
            logger.warning("Telegram notifier missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")

    def _init_drawer(self) -> None:
        self.drawer = FrameDrawer()

    def _parse_video_source(self) -> Union[int, str]:
        source = self.config.video_source
        return int(source) if source.isdigit() else source

    def _handle_key_event(self, key: int) -> bool:
        """Return False when the run loop should stop."""
        if key == ord("q"):
            logger.info("Quit requested")
            return False
        if key == ord("d"):
            self.show_display = not self.show_display
        elif key == ord("f"):
            self.show_fps = not self.show_fps
        return True

    def run(self) -> None:
        cap = cv2.VideoCapture(self._parse_video_source())

        if not cap.isOpened():
            logger.error("Open source failed: %s", self.config.video_source)
            return

        logger.info("Source opened: %s", self.config.video_source)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.info("Stream ended")
                    break

                output_frame = self._process_frame(frame)

                if self.show_display:
                    cv2.imshow("Fire Detection System", output_frame)

                key = cv2.waitKey(1) & 0xFF
                if not self._handle_key_event(key):
                    break

        except KeyboardInterrupt:
            logger.info("Interrupted")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            logger.info("Stopped")

    def _process_frame(self, frame):
        inference_result = self.detector.infer(frame)
        detections = inference_result["detections"]
        has_fire = len(detections) > 0

        if has_fire:
            max_area = max(
                max(0, (det["bbox"][2] - det["bbox"][0])) * max(0, (det["bbox"][3] - det["bbox"][1]))
                for det in detections
                if "bbox" in det
            )
            self.state_manager.set_last_fire_area(float(max_area))

        output_frame = self.drawer.draw_detections(frame, detections)
        output_frame = self.drawer.draw_status(output_frame, has_fire)

        if has_fire:
            confidence = detections[0].get("confidence", 0.0)
            now = time.time()
            if (not self.prev_has_fire) or (now - self.last_fire_log_time >= self.fire_log_interval):
                logger.warning("FIRE conf=%.2f", confidence)
                self.last_fire_log_time = now
            self._send_alert_if_due(frame, detections)
        elif self.prev_has_fire:
            logger.info("CLEAR no-fire")

        self.prev_has_fire = has_fire

        if self.show_fps:
            fps = self._calculate_fps()
            output_frame = self.drawer.draw_fps(output_frame, fps)

        return output_frame

    def _send_alert_if_due(self, frame, detections) -> None:
        if not self.state_manager.is_alert_allowed():
            return

        now = time.time()
        if now - self.last_alert_time < self.alert_cooldown:
            return

        self.last_alert_time = now

        det_info = detections[0] if detections else {}
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = (
            f"🔥 <b>FIRE DETECTED!</b>\n\n"
            f"⏰ Time: {current_time}\n"
            f"📊 Confidence: {det_info.get('confidence', 0):.2%}\n"
        )

        if self.alert_callback is not None:
            try:
                # Copy frame to avoid cross-thread mutation while async send is scheduled.
                self.alert_callback(frame.copy(), message)
            except Exception as e:
                logger.warning("Alert callback failed: %s", e)

        if self.use_builtin_notifier and self.config.notifications.send_frames:
            ok = self.notifier.send_alert(frame, message)
            if ok:
                logger.info("Alert sent")
            else:
                logger.warning("Alert send failed")

    def _calculate_fps(self) -> float:
        self.fps_counter += 1
        elapsed = time.time() - self.fps_timer

        if elapsed >= 1.0:
            fps = self.fps_counter / elapsed
            self.fps_counter = 0
            self.fps_timer = time.time()
            return fps

        return 0.0
