import subprocess
from unittest.mock import patch

from pingwatch.ping import ping_icmp, tcp_check


def _fake_run(stdout: str, returncode: int = 0):
    def _run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr="")

    return _run


def test_ping_icmp_parses_latency_from_output():
    with patch("subprocess.run", side_effect=_fake_run("64 bytes from 1.1.1.1: icmp_seq=0 time=12.3 ms")):
        assert ping_icmp("1.1.1.1") == 12.3


def test_ping_icmp_returns_none_on_nonzero_exit():
    with patch("subprocess.run", side_effect=_fake_run("Request timed out.", returncode=1)):
        assert ping_icmp("10.0.0.1") is None


def test_ping_icmp_returns_none_on_timeout_expired():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ping", timeout=1)):
        assert ping_icmp("10.0.0.1") is None


def test_tcp_check_succeeds_against_local_listener():
    import socket

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        latency = tcp_check("127.0.0.1", port)
        assert latency is not None
        assert latency >= 0
    finally:
        server.close()


def test_tcp_check_returns_none_when_nothing_listening():
    # Port 1 is a reserved/unlikely-to-be-open port for this test.
    assert tcp_check("127.0.0.1", 1, timeout_ms=200) is None
