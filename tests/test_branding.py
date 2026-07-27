from unittest.mock import MagicMock

from systemmon import branding


def test_placeholder_assets_exist_on_disk():
    assert branding.ICON_ICO_PATH.exists()
    assert branding.ICON_PNG_PATH.exists()


def test_load_tray_icon_image_opens_without_error():
    image = branding.load_tray_icon_image()
    assert image.size[0] > 0 and image.size[1] > 0


def test_set_window_icon_does_not_raise():
    import customtkinter as ctk

    window = ctk.CTk()
    try:
        branding.set_window_icon(window)
    finally:
        window.destroy()


def test_set_window_icon_applies_ico_on_windows(monkeypatch):
    # .ico via iconbitmap only renders correctly on Windows — Tk doesn't
    # raise for the mismatched format elsewhere, so this must be gated by
    # platform rather than left to a try/except to catch.
    monkeypatch.setattr(branding, "_IS_WINDOWS", True)
    window = MagicMock()

    branding.set_window_icon(window)

    window.iconbitmap.assert_called_once_with(str(branding.ICON_ICO_PATH))


def test_set_window_icon_noops_on_non_windows(monkeypatch):
    monkeypatch.setattr(branding, "_IS_WINDOWS", False)
    window = MagicMock()

    branding.set_window_icon(window)

    window.iconbitmap.assert_not_called()
