from __future__ import annotations

import numpy as np
import imagehash
from PIL import Image
from loguru import logger


class ChangeDetector:
    """Detect if key regions of the game screen have changed."""

    def __init__(self, threshold: int = 5):
        self.threshold = threshold
        self._prev_hashes: dict[str, imagehash.ImageHash] = {}

    def has_changed(self, frame: np.ndarray, regions: dict[str, tuple[int, int, int, int]]) -> bool:
        """
        Check if any region has changed.

        Args:
            frame: Full game screenshot (BGR numpy array)
            regions: Dict of {name: (x1, y1, x2, y2)} regions to check

        Returns:
            True if any region changed significantly
        """
        changed = False

        for name, (x1, y1, x2, y2) in regions.items():
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            pil_img = Image.fromarray(crop)
            current_hash = imagehash.phash(pil_img)

            prev_hash = self._prev_hashes.get(name)
            if prev_hash is not None:
                diff = abs(current_hash - prev_hash)
                if diff > self.threshold:
                    logger.debug(f"Region '{name}' changed (diff={diff})")
                    changed = True

            self._prev_hashes[name] = current_hash

        return changed

    def reset(self):
        """Clear all stored hashes."""
        self._prev_hashes.clear()
