"""
ROI region definitions for Master Duel at 1920x1080 resolution.

All coordinates are (x1, y1, x2, y2) relative to the game window.
Calibrated from actual Master Duel screenshots.
"""
from __future__ import annotations

# Base resolution for all ROI definitions
BASE_WIDTH = 1920
BASE_HEIGHT = 1080

# Key regions for change detection
CHANGE_DETECT_REGIONS = {
    "my_lp": (170, 960, 500, 1060),
    "opp_lp": (1520, 50, 1800, 145),
    "my_field": (430, 400, 1500, 700),
    "opp_field": (430, 80, 1500, 380),
    "hand": (300, 820, 1500, 1060),
    "phase": (1270, 320, 1520, 520),
}

# OCR regions for extracting text
OCR_REGIONS = {
    "my_lp": (170, 960, 500, 1060),
    "opp_lp": (1520, 50, 1800, 145),
    "phase": (1270, 320, 1520, 520),
    "my_hand": (300, 820, 1200, 1060),
    "my_monsters": (430, 450, 1250, 650),
    "opp_monsters": (430, 140, 1250, 350),
    "my_spells": (430, 650, 1250, 810),
    "opp_spells": (430, 10, 1250, 140),
}


def scale_regions(
    regions: dict[str, tuple[int, int, int, int]],
    actual_width: int,
    actual_height: int,
) -> dict[str, tuple[int, int, int, int]]:
    """Scale ROI regions from base resolution to actual resolution."""
    sx = actual_width / BASE_WIDTH
    sy = actual_height / BASE_HEIGHT
    return {
        name: (int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy))
        for name, (x1, y1, x2, y2) in regions.items()
    }
