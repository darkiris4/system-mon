from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
from typing import Optional

_IS_WINDOWS = platform.system() == "Windows"


def ping_icmp(address: str, timeout_ms: int = 1000) -> Optional[float]:
    """Sends a single ICMP echo request by shelling out to the OS ping tool.

    Returns round-trip latency in ms, or None on timeout/unreachable.
    """
    if _IS_WINDOWS:
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), address]
    else:
        # macOS/Linux ping take -W in whole seconds (Linux) or ms (macOS uses ms too,
        # but a 1s floor keeps this simple and good enough for dev-time use).
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), address]

    extra_kwargs = {}
    if _IS_WINDOWS:
        extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000) + 2,
            **extra_kwargs,
        )
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    match = re.search(r"time[=<]\s*([\d.]+)\s*ms", result.stdout, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def tcp_check(address: str, port: int, timeout_ms: int = 1000) -> Optional[float]:
    """Attempts a TCP connect as a fallback for hosts that block ICMP.

    Returns connect latency in ms, or None on failure/timeout.
    """
    start = time.perf_counter()
    try:
        with socket.create_connection((address, port), timeout=timeout_ms / 1000):
            pass
    except OSError:
        return None
    return (time.perf_counter() - start) * 1000
