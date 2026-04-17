"""Runtime state manager for alert muting and monitoring mode."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

class SystemState(str, Enum):
    NORMAL = "NORMAL"
    SILENCED = "SILENCED"
    MONITORING_INTENSELY = "MONITORING_INTENSELY"

@dataclass
class StateSnapshot:
    state: SystemState
    ignore_until: datetime | None
    last_fire_area: float
    last_fire_coverage_ratio: float
    fire_trend: str
    fire_trend_ratio: float


class StateManager:
    """In-memory short-term state transitions."""

    def __init__(
        self,
        fire_confirmation_seconds: float = 1.0,
        fire_absence_reset_seconds: float = 0.5,
        trend_threshold_ratio: float = 0.15,
        max_area_history: int = 20,
    ) -> None:
        self.mode = SystemState.NORMAL.value
        self.ignore_until = 0.0
        self.last_fire_area = 0.0
        self.last_fire_coverage_ratio = 0.0
        self.fire_confirmation_seconds = max(0.0, float(fire_confirmation_seconds))
        self.fire_absence_reset_seconds = max(0.0, float(fire_absence_reset_seconds))
        self.trend_threshold_ratio = max(0.01, float(trend_threshold_ratio))
        self.fire_start_time: float | None = None
        self.last_seen_time: float | None = None
        self.last_report_area: float | None = None
        self.area_history: deque[float] = deque(maxlen=max(2, int(max_area_history)))

    @property
    def state(self) -> SystemState:
        self._refresh_state()
        return SystemState(self.mode)

    def set_mute(self, minutes: int) -> None:
        self.mode = SystemState.SILENCED.value
        self.ignore_until = time.time() + (max(1, minutes) * 60)

    def set_monitor(self) -> None:
        if self.mode != SystemState.SILENCED.value:
            self.mode = SystemState.MONITORING_INTENSELY.value

    def resume_alerts(self) -> None:
        """Resume alerts immediately by clearing SILENCED window."""
        self.ignore_until = 0.0
        if self.mode == SystemState.SILENCED.value:
            self.mode = SystemState.NORMAL.value

    def is_alert_allowed(self) -> bool:
        self._refresh_state()
        if self.mode == SystemState.SILENCED.value and time.time() < self.ignore_until:
            return False
        return True

    def reset(self) -> None:
        self.mode = SystemState.NORMAL.value
        self.ignore_until = 0.0
        self.reset_fire_tracking()

    def set_last_fire_area(self, area: float) -> None:
        normalized_area = max(0.0, float(area))
        self.last_fire_area = normalized_area
        self.area_history.append(normalized_area)

    def set_last_fire_coverage_ratio(self, ratio: float) -> None:
        self.last_fire_coverage_ratio = max(0.0, float(ratio))

    def update_fire_presence(self, has_fire: bool, now: float | None = None) -> bool:
        """Track fire persistence over time and return confirmed fire status."""
        current_time = time.time() if now is None else float(now)

        if has_fire:
            if self.fire_start_time is None:
                self.fire_start_time = current_time
            self.last_seen_time = current_time
            return (current_time - self.fire_start_time) >= self.fire_confirmation_seconds

        if self.last_seen_time is None:
            self.reset_fire_tracking()
            return False

        # Keep fire state through short detection gaps to avoid flicker/reset on a few missed frames.
        if (current_time - self.last_seen_time) <= self.fire_absence_reset_seconds:
            if self.fire_start_time is None:
                return False
            return (current_time - self.fire_start_time) >= self.fire_confirmation_seconds

        self.reset_fire_tracking()
        return False

    def reset_fire_tracking(self) -> None:
        self.fire_start_time = None
        self.last_seen_time = None
        self.last_report_area = None
        self.area_history.clear()

    def get_fire_trend(self) -> tuple[str, float]:
        """Return fire trend label and ratio against last alert report area."""
        if self.last_fire_area <= 0:
            return "stable", 0.0

        baseline = self.last_report_area
        if baseline is None or baseline <= 0:
            if len(self.area_history) < 2:
                return "stable", 0.0
            baseline = self.area_history[-2]
            if baseline <= 0:
                return "stable", 0.0

        ratio = (self.last_fire_area - baseline) / baseline
        if ratio > self.trend_threshold_ratio:
            return "spreading", ratio
        if ratio < -self.trend_threshold_ratio:
            return "decreasing", ratio
        return "stable", ratio

    def mark_alert_reported(self) -> None:
        self.last_report_area = self.last_fire_area if self.last_fire_area > 0 else None

    # Backward-compatible aliases
    def silence_for_minutes(self, minutes: int) -> datetime:
        self.set_mute(minutes)
        return datetime.fromtimestamp(self.ignore_until, tz=UTC)

    def monitor_intensely_for_minutes(self, minutes: int) -> datetime:
        del minutes
        self.set_monitor()
        return datetime.now(UTC)

    def can_alert(self) -> bool:
        return self.is_alert_allowed()

    def snapshot(self) -> StateSnapshot:
        self._refresh_state()
        ignore_until = None
        if self.ignore_until > 0:
            ignore_until = datetime.fromtimestamp(self.ignore_until, tz=UTC)
        fire_trend, fire_trend_ratio = self.get_fire_trend()
        return StateSnapshot(
            state=SystemState(self.mode),
            ignore_until=ignore_until,
            last_fire_area=self.last_fire_area,
            last_fire_coverage_ratio=self.last_fire_coverage_ratio,
            fire_trend=fire_trend,
            fire_trend_ratio=fire_trend_ratio,
        )

    def _refresh_state(self) -> None:
        if self.mode == SystemState.SILENCED.value and time.time() >= self.ignore_until:
            self.reset()
