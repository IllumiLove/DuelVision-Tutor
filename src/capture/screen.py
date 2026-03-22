from __future__ import annotations

import numpy as np
import mss
import mss.tools
from loguru import logger

try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 not available, window detection disabled")


def find_game_window(keyword: str = "masterduel") -> dict | None:
    """Find the Master Duel window and return its bounding box."""
    if not HAS_WIN32:
        return None

    results = []

    def _enum_cb(hwnd, _results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if keyword.lower() in title.lower():
                _results.append(hwnd)

    win32gui.EnumWindows(_enum_cb, results)

    if not results:
        logger.debug(f"Window with keyword '{keyword}' not found")
        return None

    hwnd = results[0]
    rect = win32gui.GetWindowRect(hwnd)
    region = {
        "left": rect[0],
        "top": rect[1],
        "width": rect[2] - rect[0],
        "height": rect[3] - rect[1],
    }
    logger.debug(f"Found game window: {region}")
    return region


def capture_screen(region: dict | None = None) -> np.ndarray | None:
    """Capture a screen region (or full screen) and return as numpy array (BGR)."""
    with mss.mss() as sct:
        if region is None:
            monitor = sct.monitors[1]
        else:
            monitor = region

        try:
            img = sct.grab(monitor)
            frame = np.array(img)
            # mss returns BGRA, convert to BGR
            return frame[:, :, :3]
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None


def capture_game(keyword: str = "masterduel") -> tuple[np.ndarray | None, dict | None]:
    """Find game window and capture it. Returns (frame, region)."""
    region = find_game_window(keyword)
    if region is None:
        return None, None
    frame = capture_screen(region)
    return frame, region
