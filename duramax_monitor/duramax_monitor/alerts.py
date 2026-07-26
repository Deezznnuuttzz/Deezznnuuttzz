"""Simple configurable min/max threshold alerting on polled PID values."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Threshold:
    name: str  # PID name, e.g. "coolant_temp"
    min: float | None = None
    max: float | None = None


@dataclass(frozen=True)
class Alert:
    name: str
    value: float
    threshold: Threshold

    def message(self) -> str:
        if self.threshold.max is not None and self.value > self.threshold.max:
            return f"{self.name}={self.value} exceeds max {self.threshold.max}"
        if self.threshold.min is not None and self.value < self.threshold.min:
            return f"{self.name}={self.value} below min {self.threshold.min}"
        return f"{self.name}={self.value} out of range"


class AlertEngine:
    def __init__(self, thresholds: list[Threshold]):
        self._by_name = {t.name: t for t in thresholds}

    def check(self, values: dict[str, float]) -> list[Alert]:
        alerts: list[Alert] = []
        for name, value in values.items():
            threshold = self._by_name.get(name)
            if threshold is None:
                continue
            if threshold.max is not None and value > threshold.max:
                alerts.append(Alert(name=name, value=value, threshold=threshold))
            elif threshold.min is not None and value < threshold.min:
                alerts.append(Alert(name=name, value=value, threshold=threshold))
        return alerts

    @classmethod
    def from_config(cls, entries: list[dict]) -> "AlertEngine":
        thresholds = [
            Threshold(name=e["name"], min=e.get("min"), max=e.get("max")) for e in entries
        ]
        return cls(thresholds)
