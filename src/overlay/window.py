from __future__ import annotations

import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QScrollArea,
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QMouseEvent, QColor

from src.overlay.styles import OVERLAY_QSS

CIRCLED_NUMBERS = "①②③④⑤⑥⑦⑧⑨⑩"


class OverlayWindow(QWidget):
    """Transparent always-on-top overlay for displaying AI advice."""

    advice_updated = pyqtSignal(dict)

    def __init__(self, width: int = 420, height: int = 500, opacity: float = 0.88):
        super().__init__()
        self._drag_pos: QPoint | None = None
        self._last_update = 0.0
        self._capture_time = 0.0
        self._ai_time = 0.0

        self.setObjectName("overlay")
        self.setWindowTitle("DuelVision Tutor")
        self.setFixedSize(width, height)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setWindowOpacity(opacity)
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(pal.ColorRole.Window, QColor(20, 22, 40))
        self.setPalette(pal)
        self.setStyleSheet(OVERLAY_QSS)

        self._init_ui()
        self.advice_updated.connect(self._on_advice_updated)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status_time)
        self._status_timer.start(1000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Title bar
        title_bar = QHBoxLayout()
        self._title = QLabel("🎯 DuelVision Tutor")
        self._title.setObjectName("title")
        title_bar.addWidget(self._title)
        title_bar.addStretch()

        self._minimize_btn = QPushButton("─")
        self._minimize_btn.setFixedSize(24, 24)
        self._minimize_btn.setStyleSheet(
            "QPushButton { color: #888; background: transparent; border: none; font-size: 14px; }"
            " QPushButton:hover { color: white; }"
        )
        self._minimize_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(self._minimize_btn)

        layout.addLayout(title_bar)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background-color: rgb(20, 22, 40); border: none; }"
            " QScrollArea > QWidget > QWidget { background-color: rgb(20, 22, 40); }"
            " QScrollBar:vertical { width: 6px; background: transparent; }"
            " QScrollBar::handle:vertical { background: rgba(100,100,255,80); border-radius: 3px; }"
        )

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(2)
        scroll.setWidget(self._content_widget)
        layout.addWidget(scroll, 1)

        # Priority action
        self._priority_label = QLabel("等待遊戲畫面...")
        self._priority_label.setObjectName("priority")
        self._priority_label.setWordWrap(True)
        self._content_layout.addWidget(self._priority_label)

        # Steps container
        self._steps_container = QWidget()
        self._steps_layout = QVBoxLayout(self._steps_container)
        self._steps_layout.setContentsMargins(0, 0, 0, 0)
        self._steps_layout.setSpacing(0)
        self._content_layout.addWidget(self._steps_container)

        # Warnings container
        self._warnings_container = QWidget()
        self._warnings_layout = QVBoxLayout(self._warnings_container)
        self._warnings_layout.setContentsMargins(0, 0, 0, 0)
        self._warnings_layout.setSpacing(0)
        self._content_layout.addWidget(self._warnings_container)

        # Assessment
        self._assessment_label = QLabel("")
        self._assessment_label.setObjectName("assessment")
        self._assessment_label.setWordWrap(True)
        self._content_layout.addWidget(self._assessment_label)

        self._content_layout.addStretch()

        # Status bar
        self._status_label = QLabel("就緒")
        self._status_label.setObjectName("status")
        layout.addWidget(self._status_label)

    def update_advice(self, advice: dict):
        """Thread-safe advice update."""
        self.advice_updated.emit(advice)

    def _on_advice_updated(self, advice: dict):
        """Update UI with new advice (runs on Qt thread)."""
        self._last_update = time.time()

        priority = advice.get("priority_action", "無建議")
        self._priority_label.setText(f"▶ {priority}")

        # Rebuild steps
        self._clear_layout(self._steps_layout)
        for step_info in advice.get("action_steps", []):
            step_num = step_info.get("step", 0)
            action = step_info.get("action", "")
            reason = step_info.get("reason", "")

            if 1 <= step_num <= 10:
                prefix = CIRCLED_NUMBERS[step_num - 1]
            else:
                prefix = f"({step_num})"

            step_label = QLabel(f"{prefix} {action}")
            step_label.setObjectName("step")
            step_label.setWordWrap(True)
            self._steps_layout.addWidget(step_label)

            if reason:
                reason_label = QLabel(f"  → {reason}")
                reason_label.setObjectName("reason")
                reason_label.setWordWrap(True)
                self._steps_layout.addWidget(reason_label)

        # Rebuild warnings
        self._clear_layout(self._warnings_layout)
        for warning in advice.get("warnings", []):
            warn_label = QLabel(f"⚠ {warning}")
            warn_label.setObjectName("warning")
            warn_label.setWordWrap(True)
            self._warnings_layout.addWidget(warn_label)

        assessment = advice.get("win_assessment", "")
        self._assessment_label.setText(f"📊 {assessment}" if assessment else "")
        self._update_status()

    def set_timing(self, capture_ms: float = 0, ai_ms: float = 0):
        """Set timing info for status bar."""
        self._capture_time = capture_ms
        self._ai_time = ai_ms
        self._update_status()

    def _update_status(self):
        elapsed = time.time() - self._last_update if self._last_update else 0
        parts = []
        if self._capture_time > 0:
            parts.append(f"截圖: {self._capture_time:.0f}ms")
        if self._ai_time > 0:
            parts.append(f"AI: {self._ai_time:.0f}ms")
        if elapsed > 0:
            parts.append(f"更新: {elapsed:.0f}s前")
        self._status_label.setText(" | ".join(parts) if parts else "就緒")

    def _update_status_time(self):
        if self._last_update > 0:
            self._update_status()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_waiting(self, message: str = "等待遊戲畫面..."):
        """Show waiting state."""
        self._priority_label.setText(message)
        self._clear_layout(self._steps_layout)
        self._clear_layout(self._warnings_layout)
        self._assessment_label.setText("")
        self._status_label.setText("掃描中...")

    # --- Drag support ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
