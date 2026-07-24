from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Host:
    name: str
    address: str
    method: str = "icmp"  # "icmp" or "tcp"
    port: Optional[int] = None  # required when method == "tcp"
    interval_sec: int = 5

    # Overrides; fall back to GlobalSettings defaults when None.
    latency_warning_ms: Optional[int] = None
    consecutive_miss_threshold: Optional[int] = None
    rolling_loss_window: Optional[int] = None
    rolling_loss_pct: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Host":
        return cls(**data)


@dataclass
class GlobalSettings:
    default_latency_warning_ms: int = 150
    default_consecutive_miss_threshold: int = 3
    default_rolling_loss_window: int = 20
    default_rolling_loss_pct: float = 20.0
    retention_days: int = 30
    autostart: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GlobalSettings":
        return cls(**data)
