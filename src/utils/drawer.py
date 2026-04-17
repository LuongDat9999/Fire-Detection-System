"""Visualization utilities for drawing detections on frames."""

import cv2
import numpy as np
from typing import List, Dict


class FrameDrawer:
    """Draw detections and simple status text."""

    def __init__(self):
        self.fire_color = (0, 0, 255)
        self.text_color = (255, 255, 255)
        self.ok_color = (0, 200, 0)

    def draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        output_frame = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            confidence = det.get("confidence", 0.0)

            cv2.rectangle(output_frame, (x1, y1), (x2, y2), self.fire_color, 2)

            label = f"Fire: {confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(
                output_frame,
                (x1, y1 - label_size[1] - 4),
                (x1 + label_size[0], y1),
                self.fire_color,
                -1,
            )
            cv2.putText(
                output_frame,
                label,
                (x1, y1 - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                self.text_color,
                1,
            )

        return output_frame

    def draw_status(self, frame: np.ndarray, has_fire: bool) -> np.ndarray:
        output_frame = frame.copy()
        status_text = "FIRE DETECTED" if has_fire else "Monitoring"
        status_color = self.fire_color if has_fire else self.ok_color

        cv2.rectangle(output_frame, (0, 0), (260, 45), (0, 0, 0), -1)
        cv2.putText(
            output_frame,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2,
        )

        return output_frame

    def draw_fps(self, frame: np.ndarray, fps: float) -> np.ndarray:
        output_frame = frame.copy()
        cv2.putText(
            output_frame,
            f"FPS: {fps:.1f}",
            (frame.shape[1] - 150, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            self.text_color,
            1,
        )
        return output_frame
