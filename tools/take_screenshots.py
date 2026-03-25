"""
自動截圖工具 — 用 Demo 資料渲染各疊加 UI 狀態並存圖至 docs/screenshots/
執行方式：python tools/take_screenshots.py
"""
from __future__ import annotations

import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QScreen

# ── 輸出資料夾
OUT_DIR = ROOT / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

app = QApplication(sys.argv)

from src.overlay.window import OverlayWindow  # noqa: E402 (after QApplication)

# ── 各截圖場景定義
SCENARIOS = [
    # (filename, advice_dict, timing, set_waiting)
    (
        "overlay_main.png",
        {
            "priority_action": "特召「蛇眼の炎龍」，觸發效果，加入手牌 1 張火屬性怪獸",
            "action_steps": [
                {"step": 1, "action": "手牌「原罪寶 — 蛇眼」效果發動", "reason": "免費特召，條件無限制"},
                {"step": 2, "action": "特召「蛇眼の炎龍」從卡組", "reason": "展開核心，提供後續效果"},
                {"step": 3, "action": "炎龍效果：將「炎妖蟲の蛹」置於對方場上", "reason": "為連接召喚準備素材"},
                {"step": 4, "action": "連接召喚「I:Pマスカレーナ」", "reason": "對方回合可繼續展開"},
            ],
            "warnings": [
                "⚠ 本回合已通常召喚「WANTED: 懸賞境界盜賊」，無法再次通召",
            ],
            "win_assessment": "目前場面優勢 — 保持壓制，對方手牌剩 3 張",
        },
        (210, 1430),
        False,
    ),
    (
        "overlay_advice.png",
        {
            "priority_action": "手牌誘發！發動「灰流麗」阻止對方展開",
            "action_steps": [
                {"step": 1, "action": "對方發動「烙印融合」", "reason": "從額外卡組特召，灰流麗可阻斷"},
                {"step": 2, "action": "從手牌捨棄「灰流麗」", "reason": "免費發動，效果無效化"},
                {"step": 3, "action": "目標：對方無法從卡組特召此回合", "reason": "壓制對方核心展開"},
            ],
            "warnings": [
                "灰流麗只能阻止「從卡組」的效果，請確認觸發對象",
                "此後手牌剩 2 張，需謹慎對應後續連鎖",
            ],
            "win_assessment": "手牌優勢 — 保留至少 1 張手坑應對後續",
        },
        (185, 980),
        False,
    ),
    (
        "game_state.png",
        {
            "priority_action": "解析完成 — LP 我方 8000 / 對方 5400",
            "action_steps": [
                {"step": 1, "action": "我方手牌 (5 張)：灰流麗、無限泡影、原罪寶、蛇眼炎龍、I:P 馬斯卡羅拿", "reason": "手牌資訊已同步"},
                {"step": 2, "action": "場上：炎妖蟲の蛹（對方控制）、藤蛇（守備）", "reason": "怪獸區狀態已識別"},
                {"step": 3, "action": "當前階段：主要階段 1", "reason": "可進行所有操作"},
            ],
            "warnings": [],
            "win_assessment": "OCR 識別率 97.3% | 卡名比對完成 5/5",
        },
        (312, 0),
        False,
    ),
    (
        "deck_select.png",
        None,
        (0, 0),
        True,  # waiting state for deck selection screen
    ),
]


def grab_and_save(window: OverlayWindow, path: pathlib.Path):
    pixmap = window.grab()  # QWidget.grab() — directly renders widget to pixmap
    pixmap.save(str(path))
    print(f"  已儲存：{path.relative_to(ROOT)} ({pixmap.width()}×{pixmap.height()})")


windows: list[OverlayWindow] = []


def run_scenarios():
    screen_geom = app.primaryScreen().geometry()
    base_x = max(screen_geom.width() - 460, 20)

    for i, (filename, advice, timing, is_waiting) in enumerate(SCENARIOS):
        win = OverlayWindow(width=420, height=500, opacity=1.0)  # opacity=1 for clean screenshot
        # 移除 FramelessWindowHint 不影響疊加，但讓視窗可正常顯示
        win.move(base_x, 20 + i * 10)  # stack slightly
        win.show()

        if is_waiting:
            win.set_waiting("請選擇卡組...")
        elif advice:
            win._on_advice_updated(advice)
            win.set_timing(capture_ms=timing[0], ai_ms=timing[1])

        windows.append((win, filename))

    # 等所有視窗渲染完成後截圖
    def do_capture():
        for win, filename in windows:
            out_path = OUT_DIR / filename
            grab_and_save(win, out_path)
            win.close()
        print("\n✅ 截圖完成！共", len(windows), "張")
        app.quit()

    QTimer.singleShot(600, do_capture)


QTimer.singleShot(100, run_scenarios)
sys.exit(app.exec())
