"""Wallpaper mode platform guard: import-safe everywhere, structured refusal off Windows."""

from __future__ import annotations

import asyncio
import os


def test_wallpaper_modules_import_safely_on_any_platform() -> None:
    import wallpaper.pointer_wheel_forwarder  # noqa: F401
    import wallpaper.wallpaper_engine_bridge  # noqa: F401
    import wallpaper.windows_desktop_layer  # noqa: F401


def test_wallpaper_desktop_mode_refuses_cleanly_off_windows() -> None:
    from server.handlers.wallpaper_handler import WallpaperHandler

    if os.name == "nt":
        import pytest

        pytest.skip("guard only applies off Windows")

    handler = WallpaperHandler()
    result = asyncio.run(handler._start({}))
    assert result is not None
    assert result["ok"] is False
    assert result["error"] == "wallpaper_unsupported_platform"
    assert result["suggestion"] == "browser"


def test_wallpaper_desktop_mode_explicit_refusal_off_windows() -> None:
    from server.handlers.wallpaper_handler import WallpaperHandler

    if os.name == "nt":
        import pytest

        pytest.skip("guard only applies off Windows")

    handler = WallpaperHandler()
    result = asyncio.run(handler._start({"mode": "desktop"}))
    assert result["ok"] is False
    assert result["error"] == "wallpaper_unsupported_platform"
