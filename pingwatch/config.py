from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .models import GlobalSettings, Host

DEFAULT_CONFIG_PATH = Path("config.json")


@dataclass
class AppConfig:
    hosts: List[Host] = field(default_factory=list)
    settings: GlobalSettings = field(default_factory=GlobalSettings)

    def to_dict(self) -> dict:
        return {
            "hosts": [h.to_dict() for h in self.hosts],
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        return cls(
            hosts=[Host.from_dict(h) for h in data.get("hosts", [])],
            settings=GlobalSettings.from_dict(data.get("settings", {})),
        )


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    if not path.exists():
        return AppConfig()
    with path.open("r", encoding="utf-8") as f:
        return AppConfig.from_dict(json.load(f))


def save_config(config: AppConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Writes via a temp file + atomic replace so a crash mid-write can't corrupt config.json."""
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)
    tmp_path.replace(path)
