from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from .models import GlobalSettings, Host
from .paths import app_dir

DEFAULT_CONFIG_PATH = app_dir() / "config.json"

# Event statuses for config changes, logged alongside host up/down transitions
# (see logging_store.append_event) so Settings edits show up in the same
# events.log a user already greps for troubleshooting.
HOST_ADDED = "HOST_ADDED"
HOST_EDITED = "HOST_EDITED"
HOST_REMOVED = "HOST_REMOVED"
SETTINGS_CHANGED = "SETTINGS_CHANGED"


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


def _describe_host(host: Host) -> str:
    port_suffix = f":{host.port}" if host.method == "tcp" and host.port else ""
    return f"{host.address}, {host.method}{port_suffix}"


def _field_diff(old, new) -> str:
    """Renders the changed fields between two dataclass instances of the same type."""
    changes = []
    for f in dataclasses.fields(old):
        old_val = getattr(old, f.name)
        new_val = getattr(new, f.name)
        if old_val != new_val:
            changes.append(f"{f.name}: {old_val} -> {new_val}")
    return ", ".join(changes)


def diff_events(old: AppConfig, new: AppConfig) -> List[Tuple[str, str, str]]:
    """Summarizes host add/edit/remove and global settings changes between two
    configs as (status, host_name, detail) tuples ready for logging_store.append_event.

    Hosts are matched by name, so a rename shows up as a remove + an add
    rather than an edit — there's no other stable identity to match on.
    """
    events: List[Tuple[str, str, str]] = []

    old_hosts = {h.name: h for h in old.hosts}
    new_hosts = {h.name: h for h in new.hosts}

    for name, host in new_hosts.items():
        if name not in old_hosts:
            events.append((HOST_ADDED, name, _describe_host(host)))
        elif host != old_hosts[name]:
            events.append((HOST_EDITED, name, _field_diff(old_hosts[name], host)))

    for name, host in old_hosts.items():
        if name not in new_hosts:
            events.append((HOST_REMOVED, name, _describe_host(host)))

    if new.settings != old.settings:
        events.append((SETTINGS_CHANGED, "", _field_diff(old.settings, new.settings)))

    return events
