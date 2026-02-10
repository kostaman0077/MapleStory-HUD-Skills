"""Interactive calibration tool for selecting the skill-bar region and slots.

Launch with:  ``python main.py --calibrate``

The user draws a rectangle over the skill bar. Then they enter how many
skill slots there are, and the region is divided into even columns.
Results are saved to ``config.json``.
"""

from __future__ import annotations

import sys
from typing import Optional

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QScreen
from PyQt6.QtWidgets import QApplication, QInputDialog, QWidget

from config import load_config, save_config


class _CalibrationOverlay(QWidget):
    """Full-screen semi-transparent overlay for rectangle selection."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        screen: QScreen = QApplication.primaryScreen()
        geo = screen.geometry()
        self.setGeometry(geo)

        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self._final_rect: Optional[QRect] = None

    # --- mouse events ---

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.globalPosition().toPoint()
            self._current = self._origin

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._origin is not None:
            self._current = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._origin:
            self._current = event.globalPosition().toPoint()
            self._final_rect = QRect(self._origin, self._current).normalized()
            self.close()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._final_rect = None
            self.close()

    # --- painting ---

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim the screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # Draw instructions
        font = QFont("Segoe UI", 18)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
            "\n\nDraw a rectangle over your skill bar  •  ESC to cancel",
        )

        # Draw selection rectangle
        if self._origin and self._current:
            rect = QRect(self._origin, self._current).normalized()
            pen = QPen(QColor(0, 200, 255), 2)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 200, 255, 40))
            painter.drawRect(rect)

        painter.end()

    @property
    def selected_rect(self) -> Optional[QRect]:
        return self._final_rect


def run_calibration(config_path: str = "config.json") -> bool:
    """Run the interactive calibration flow. Returns True on success."""
    app = QApplication.instance() or QApplication(sys.argv)

    overlay = _CalibrationOverlay()
    overlay.showFullScreen()
    app.exec()

    rect = overlay.selected_rect
    if rect is None or rect.width() < 10 or rect.height() < 10:
        print("[calibration] Cancelled or invalid selection.")
        return False

    print(f"[calibration] Selected region: x={rect.x()} y={rect.y()} "
          f"w={rect.width()} h={rect.height()}")

    # Ask for slot count
    slot_count, ok = QInputDialog.getInt(
        None,
        "Skill Slots",
        "How many skill slots are in the bar?",
        value=4, min=1, max=20,
    )
    if not ok:
        print("[calibration] Cancelled.")
        return False

    # Build slot definitions (evenly divided)
    slot_w = rect.width() // slot_count
    slot_h = rect.height()
    slots = []
    for i in range(slot_count):
        slots.append({
            "name": f"Skill {i + 1}",
            "x": i * slot_w,
            "y": 0,
            "w": slot_w,
            "h": slot_h,
        })

    # Save
    cfg = load_config(config_path)
    cfg["skill_bar_region"] = {
        "x": rect.x(),
        "y": rect.y(),
        "w": rect.width(),
        "h": rect.height(),
    }
    cfg["slots"] = slots
    save_config(config_path, cfg)
    print(f"[calibration] Saved {slot_count} slots to {config_path}")
    return True
