import sys
from unittest.mock import MagicMock, patch

from systemmon import autostart


def test_is_supported_reflects_platform():
    with patch("systemmon.autostart.platform.system", return_value="Windows"):
        assert autostart.is_supported() is True
    with patch("systemmon.autostart.platform.system", return_value="Darwin"):
        assert autostart.is_supported() is False


def test_set_autostart_is_noop_when_unsupported():
    with patch("systemmon.autostart.platform.system", return_value="Darwin"):
        # Must not raise even though winreg doesn't exist on this platform.
        autostart.set_autostart(True)


def test_set_autostart_writes_registry_value_on_windows():
    fake_winreg = MagicMock()
    fake_key = MagicMock()
    fake_winreg.OpenKey.return_value.__enter__.return_value = fake_key

    with patch("systemmon.autostart.platform.system", return_value="Windows"), patch.dict(
        sys.modules, {"winreg": fake_winreg}
    ):
        autostart.set_autostart(True)

    args, _ = fake_winreg.SetValueEx.call_args
    assert args[0] is fake_key
    assert args[1] == "SystemMon"


def test_set_autostart_deletes_registry_value_when_disabled():
    fake_winreg = MagicMock()
    fake_key = MagicMock()
    fake_winreg.OpenKey.return_value.__enter__.return_value = fake_key

    with patch("systemmon.autostart.platform.system", return_value="Windows"), patch.dict(
        sys.modules, {"winreg": fake_winreg}
    ):
        autostart.set_autostart(False)

    fake_winreg.DeleteValue.assert_called_once_with(fake_key, "SystemMon")


def test_is_autostart_enabled_false_when_unsupported():
    with patch("systemmon.autostart.platform.system", return_value="Darwin"):
        assert autostart.is_autostart_enabled() is False
