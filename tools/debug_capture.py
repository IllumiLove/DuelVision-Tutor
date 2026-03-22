"""
Debug tool: Capture one frame and save each ROI region + OCR results.
Usage: python tools/debug_capture.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import cv2
import numpy as np
from pathlib import Path
from src.capture.screen import capture_game
from src.parser.ocr_engine import OCREngine
from src.parser.regions import OCR_REGIONS, CHANGE_DETECT_REGIONS, scale_regions
from src.config import load_config

DEBUG_DIR = Path(__file__).parent.parent / "data" / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def main():
    config = load_config()
    print(f"Searching for window: {config.capture.target_window}")

    frame, region = capture_game(config.capture.target_window)
    if frame is None:
        print("ERROR: Game window not found!")
        print("Make sure Master Duel is running.")
        return

    w = region["width"]
    h = region["height"]
    print(f"Window found: {region}")
    print(f"Frame shape: {frame.shape}")

    # Save full screenshot
    full_path = DEBUG_DIR / "full_frame.png"
    cv2.imwrite(str(full_path), frame)
    print(f"\nSaved full frame: {full_path}")

    # Scale regions
    regions = scale_regions(OCR_REGIONS, w, h)
    print(f"\nScaled OCR regions (for {w}x{h}):")
    for name, coords in regions.items():
        print(f"  {name}: {coords}")

    # Init OCR
    print("\nLoading OCR engine...")
    ocr = OCREngine(use_gpu=config.ocr.use_gpu, lang=config.ocr.language)

    # Test each region
    print("\n" + "=" * 60)
    print("OCR Results per Region")
    print("=" * 60)

    for name, (x1, y1, x2, y2) in regions.items():
        # Clamp to frame bounds
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(fw, x2), min(fh, y2)

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            print(f"\n[{name}] EMPTY CROP at ({x1},{y1},{x2},{y2})")
            continue

        # Save cropped region
        crop_path = DEBUG_DIR / f"region_{name}.png"
        cv2.imwrite(str(crop_path), crop)

        # Also save preprocessed version
        preprocessed = ocr.preprocess(crop)
        pre_path = DEBUG_DIR / f"region_{name}_pre.png"
        cv2.imwrite(str(pre_path), preprocessed)

        # OCR
        results_raw = ocr.recognize(crop, preprocess=False)
        results_pre = ocr.recognize(crop, preprocess=True)

        print(f"\n[{name}] Region: ({x1},{y1}) to ({x2},{y2}), Size: {crop.shape[1]}x{crop.shape[0]}")
        print(f"  Raw OCR ({len(results_raw)} texts):")
        for text, conf in results_raw:
            print(f"    '{text}' (conf={conf:.3f})")
        print(f"  Preprocessed OCR ({len(results_pre)} texts):")
        for text, conf in results_pre:
            print(f"    '{text}' (conf={conf:.3f})")

    # Draw all regions on the full frame for visualization
    vis = frame.copy()
    colors = {
        "my_lp": (0, 255, 0),
        "opp_lp": (0, 0, 255),
        "my_hand": (255, 255, 0),
        "my_monsters": (255, 0, 255),
        "opp_monsters": (0, 255, 255),
        "my_spells": (128, 255, 0),
        "opp_spells": (0, 128, 255),
        "phase": (255, 128, 0),
    }
    for name, (x1, y1, x2, y2) in regions.items():
        color = colors.get(name, (200, 200, 200))
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, name, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    vis_path = DEBUG_DIR / "regions_overlay.png"
    cv2.imwrite(str(vis_path), vis)
    print(f"\nSaved regions overlay: {vis_path}")
    print(f"\nAll debug images saved to: {DEBUG_DIR}")


if __name__ == "__main__":
    main()
