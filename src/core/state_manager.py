"""Runtime state manager for alert muting and monitoring mode."""

from __future__ import annotations

import time
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


class StateManager:
    """In-memory short-term state transitions."""

    def __init__(self) -> None:
        self.mode = SystemState.NORMAL.value
        self.ignore_until = 0.0
        self.last_fire_area = 0.0

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

    def is_alert_allowed(self) -> bool:
        self._refresh_state()
        if self.mode == SystemState.SILENCED.value and time.time() < self.ignore_until:
            return False
        return True

    def reset(self) -> None:
        self.mode = SystemState.NORMAL.value
        self.ignore_until = 0.0

    def set_last_fire_area(self, area: float) -> None:
        self.last_fire_area = max(0.0, float(area))

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
        return StateSnapshot(
            state=SystemState(self.mode),
            ignore_until=ignore_until,
            last_fire_area=self.last_fire_area,
        )

    def _refresh_state(self) -> None:
        if self.mode == SystemState.SILENCED.value and time.time() >= self.ignore_until:
            self.reset()
