from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import List, Optional, Tuple

from .paths import app_dir

LOGS_DIR = app_dir() / "logs"

# (timestamp, latency_ms or None on timeout, status)
RawPoint = Tuple[dt.datetime, Optional[float], str]


def _raw_log_path(host_name: str, date: dt.date, logs_dir: Path = LOGS_DIR) -> Path:
    return logs_dir / host_name / f"{date.isoformat()}.csv"


def append_raw_ping(
    host_name: str,
    status: str,
    latency_ms: Optional[float],
    *,
    when: Optional[dt.datetime] = None,
    logs_dir: Path = LOGS_DIR,
) -> None:
    """Appends one row per ping to today's per-host CSV. Status leads the row for easy grepping."""
    when = when or dt.datetime.now()
    path = _raw_log_path(host_name, when.date(), logs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["status", "timestamp", "latency_ms"])
        writer.writerow(
            [
                status,
                when.isoformat(timespec="seconds"),
                "" if latency_ms is None else f"{latency_ms:.1f}",
            ]
        )


def append_event(
    host_name: str,
    status: str,
    detail: str = "",
    *,
    when: Optional[dt.datetime] = None,
    logs_dir: Path = LOGS_DIR,
) -> None:
    """Records a state transition (not routine pings) to the combined events log.

    Kept separate from the per-day raw CSVs so scanning for problems doesn't
    mean wading through thousands of routine OK rows.
    """
    when = when or dt.datetime.now()
    path = logs_dir / "events.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{status},{when.isoformat(timespec='seconds')},{host_name}"
    if detail:
        line += f",{detail}"
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_recent_raw(
    host_name: str,
    *,
    since: Optional[dt.datetime] = None,
    now: Optional[dt.datetime] = None,
    logs_dir: Path = LOGS_DIR,
) -> List[RawPoint]:
    """Reads raw ping rows for a host between `since` and `now` (default: the last hour).

    May span two per-day files when the window crosses midnight, since each
    raw log file covers exactly one day.
    """
    now = now or dt.datetime.now()
    since = since or (now - dt.timedelta(hours=1))

    records: List[RawPoint] = []
    host_dir = logs_dir / host_name
    if not host_dir.exists():
        return records

    date = since.date()
    while date <= now.date():
        path = host_dir / f"{date.isoformat()}.csv"
        if path.exists():
            with path.open("r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    timestamp = dt.datetime.fromisoformat(row["timestamp"])
                    if since <= timestamp <= now:
                        latency = float(row["latency_ms"]) if row["latency_ms"] else None
                        records.append((timestamp, latency, row["status"]))
        date += dt.timedelta(days=1)

    records.sort(key=lambda record: record[0])
    return records


def prune_old_logs(
    retention_days: int,
    *,
    today: Optional[dt.date] = None,
    logs_dir: Path = LOGS_DIR,
) -> None:
    """Deletes per-day raw CSV files older than the retention window.

    Whole files are deleted rather than filtering rows within a file, since
    each file already covers exactly one day.
    """
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=retention_days)
    if not logs_dir.exists():
        return
    for host_dir in logs_dir.iterdir():
        if not host_dir.is_dir():
            continue
        for csv_file in host_dir.glob("*.csv"):
            try:
                file_date = dt.date.fromisoformat(csv_file.stem)
            except ValueError:
                continue
            if file_date < cutoff:
                csv_file.unlink()
