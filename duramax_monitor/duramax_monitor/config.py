"""Loads config.yaml (connection settings, polled PIDs, alert thresholds,
verified enhanced PIDs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .enhanced_pids import EnhancedPid, load_from_config as load_enhanced_from_config


@dataclass
class Config:
    connection_uri: str = "sim://"
    timeout: float = 2.0
    interval: float = 0.5
    pids: list[str] = field(default_factory=list)
    log_csv: str | None = None
    alert_entries: list[dict] = field(default_factory=list)
    enhanced_pids: dict[int, EnhancedPid] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        data = yaml.safe_load(Path(path).read_text()) or {}
        conn = data.get("connection", {})
        mon = data.get("monitor", {})
        return cls(
            connection_uri=conn.get("uri", "sim://"),
            timeout=float(conn.get("timeout", 2.0)),
            interval=float(mon.get("interval", 0.5)),
            pids=list(mon.get("pids", [])),
            log_csv=mon.get("log_csv"),
            alert_entries=list(data.get("alerts", [])),
            enhanced_pids=load_enhanced_from_config(data.get("enhanced_pids", [])),
        )
