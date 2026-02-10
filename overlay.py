"""Vertical Sidebar Overlay for 32+ skills."""

import time
from typing import List, Optional

import cv2
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QScreen, QIcon, QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout

from vision import SkillState



class SkillWidget(QFrame):
    """Visual representation of a single skill slot.

    Shows the live crop of the skill slot.
    """

    def __init__(self, name: str, index: int, size: int = 80) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self.name = name
        self.index = index
        self.on_cooldown = False
        self.elapsed = 0.0
        
        # Base style: transparent background, slight border
        self.setStyleSheet(f"background-color: transparent; border: 1px solid rgba(255, 255, 255, 50); border-radius: 4px;")

        # Image Label (Background)
        self.image_label = QLabel(self)
        self.image_label.setGeometry(0, 0, size, size)
        self.image_label.setScaledContents(True)
        
        # Overlay Label (Foreground - for Red tint and Text)
        self.overlay_label = QLabel(self)
        self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay_label.setGeometry(0, 0, size, size)
        # Font size proportional to widget size
        font_size = int(size * 0.4)
        self.overlay_label.setStyleSheet(f"color: white; font-weight: bold; font-size: {font_size}px; background: transparent; border: none;")
        self.overlay_label.hide()

    def update_state(self, state: SkillState) -> None:
        # 1. Update Image
        if state.image is not None and state.image.size > 0:
            h, w, ch = state.image.shape
            bytes_per_line = ch * w
            # OpenCV is BGR, Qt expects RGB.
            # We can convert here or let Qt handle it (swapping channels usually cheaper in cv2)
            rgb_image = cv2.cvtColor(state.image, cv2.COLOR_BGR2RGB)
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(q_img))
        else:
            self.image_label.clear()

        # 2. Update Cooldown Status
        if state.on_cooldown:
            if not self.on_cooldown:
                self.on_cooldown = True
                self.started_at = time.monotonic()
                # Semi-transparent red overlay
                self.overlay_label.setStyleSheet(f"background-color: rgba(255, 0, 0, 150); color: white; font-weight: bold; font-size: {int(self.width()*0.4)}px; border-radius: 4px;")
                self.overlay_label.show()
            
            self.elapsed = time.monotonic() - self.started_at
            self.overlay_label.setText(f"{self.elapsed:.0f}")
        else:
            if self.on_cooldown:
                self.on_cooldown = False
                self.overlay_label.hide()



class SidebarOverlay(QWidget):
    """Vertical sidebar docking to the right side of the screen."""

    # Signal to request opening settings
    open_settings = pyqtSignal()

    def __init__(self, slots: List[dict], scale: float = 1.0, config_path: str = "config.json") -> None:
        super().__init__()
        self.config_path = config_path
        self._scale = scale
        self._slots = slots
        
        # Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Draggable state
        self._dragging = False
        self._drag_start_pos = QPoint()

        # Layout
        self._layout = QGridLayout(self)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(10, 10, 10, 10)

        self.widgets: dict[str, SkillWidget] = {}
        self.rebuild_ui()

        # Load position from config if available (done in main, or we do it here if passed)
        # For now, initial position is handled by caller or defaults.

    def rebuild_ui(self) -> None:
        """Clear and rebuild the layout based on current slots and scale."""
        # Clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.widgets.clear()

        # Constants
        COLS = 2 if len(self._slots) > 16 else 1
        ICON_SIZE = int(80 * self._scale)

        for i, slot in enumerate(self._slots):
            w = SkillWidget(slot["name"], i, size=ICON_SIZE)
            row = i // COLS
            col = i % COLS
            self._layout.addWidget(w, row, col)
            self.widgets[slot["name"]] = w
        
        self.adjustSize()

    def set_scale(self, scale: float) -> None:
        """Update scale and rebuild UI."""
        if scale != self._scale:
            self._scale = scale
            self.rebuild_ui()

    def update_slots(self, slots: List[dict]) -> None:
        """Update the list of slots."""
        self._slots = slots
        self.rebuild_ui()

    @pyqtSlot(list)
    def update_skills(self, states: List[SkillState]) -> None:
        for st in states:
            if st.name in self.widgets:
                self.widgets[st.name].update_state(st)

    # --- Dragging Logic ---

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.save_position()
            event.accept()

    def contextMenuEvent(self, event) -> None:
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        action_settings = menu.addAction("Settings")
        action_exit = menu.addAction("Exit")
        
        action = menu.exec(event.globalPos())
        
        if action == action_settings:
            self.open_settings.emit()
        elif action == action_exit:
            QApplication.quit()

    def save_position(self) -> None:
        """Save current position to config."""
        from config import load_config, save_config
        cfg = load_config(self.config_path)
        cfg["window_x"] = self.x()
        cfg["window_y"] = self.y()
        save_config(self.config_path, cfg)


