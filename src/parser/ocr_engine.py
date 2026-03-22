from __future__ import annotations

import cv2
import numpy as np
from loguru import logger


class OCREngine:
    """PaddleOCR wrapper for game text recognition (v3.x API)."""

    def __init__(self, use_gpu: bool = True, lang: str = "chinese_cht"):
        self._ocr = None
        self._use_gpu = use_gpu
        self._lang = lang

    def _ensure_loaded(self):
        if self._ocr is None:
            import os
            os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                lang=self._lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
            logger.info(f"PaddleOCR loaded (gpu={self._use_gpu}, lang={self._lang})")

    def preprocess(self, img: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR accuracy."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def recognize(self, img: np.ndarray, preprocess: bool = True) -> list[tuple[str, float]]:
        """Run OCR on an image region. Returns list of (text, confidence) tuples."""
        self._ensure_loaded()

        if preprocess:
            img = self.preprocess(img)

        try:
            results = self._ocr.predict(img)
            if not results:
                return []

            r = results[0]
            rec_texts = r.get("rec_texts", [])
            rec_scores = r.get("rec_scores", [])
            return list(zip(rec_texts, rec_scores))
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return []

    def recognize_region(
        self,
        frame: np.ndarray,
        region: tuple[int, int, int, int],
        preprocess: bool = True,
    ) -> list[tuple[str, float]]:
        """Run OCR on a specific region of a frame."""
        x1, y1, x2, y2 = region
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return []
        return self.recognize(crop, preprocess=preprocess)

    def recognize_number(
        self, frame: np.ndarray, region: tuple[int, int, int, int]
    ) -> int | None:
        """Recognize a number (like LP) from a region."""
        texts = self.recognize_region(frame, region)
        for text, _conf in texts:
            digits = "".join(c for c in text if c.isdigit())
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    continue
        return None
