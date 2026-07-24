import csv
import datetime as dt
from pathlib import Path

from pingwatch import logging_store


def test_append_raw_ping_writes_header_then_status_first_rows(tmp_path: Path):
    when = dt.datetime(2026, 7, 24, 10, 0, 0)
    logging_store.append_raw_ping("router1", "OK", 12.3, when=when, logs_dir=tmp_path)
    logging_store.append_raw_ping("router1", "DOWN", None, when=when, logs_dir=tmp_path)

    path = tmp_path / "router1" / "2026-07-24.csv"
    rows = list(csv.reader(path.open()))

    assert rows[0] == ["status", "timestamp", "latency_ms"]
    assert rows[1] == ["OK", "2026-07-24T10:00:00", "12.3"]
    assert rows[2] == ["DOWN", "2026-07-24T10:00:00", ""]


def test_append_raw_ping_separates_files_by_day(tmp_path: Path):
    logging_store.append_raw_ping("router1", "OK", 1.0, when=dt.datetime(2026, 7, 23, 23, 59), logs_dir=tmp_path)
    logging_store.append_raw_ping("router1", "OK", 1.0, when=dt.datetime(2026, 7, 24, 0, 1), logs_dir=tmp_path)

    host_dir = tmp_path / "router1"
    assert sorted(p.name for p in host_dir.glob("*.csv")) == ["2026-07-23.csv", "2026-07-24.csv"]


def test_append_event_writes_status_first_combined_line(tmp_path: Path):
    when = dt.datetime(2026, 7, 24, 10, 0, 0)
    logging_store.append_event("router1", "DOWN", "timeout", when=when, logs_dir=tmp_path)

    line = (tmp_path / "events.log").read_text().strip()
    assert line == "DOWN,2026-07-24T10:00:00,router1,timeout"


def test_prune_old_logs_deletes_only_files_past_retention(tmp_path: Path):
    logging_store.append_raw_ping("router1", "OK", 1.0, when=dt.datetime(2026, 6, 1), logs_dir=tmp_path)
    logging_store.append_raw_ping("router1", "OK", 1.0, when=dt.datetime(2026, 7, 20), logs_dir=tmp_path)

    logging_store.prune_old_logs(30, today=dt.date(2026, 7, 24), logs_dir=tmp_path)

    remaining = sorted(p.name for p in (tmp_path / "router1").glob("*.csv"))
    assert remaining == ["2026-07-20.csv"]
