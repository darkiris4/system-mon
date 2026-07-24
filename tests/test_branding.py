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
