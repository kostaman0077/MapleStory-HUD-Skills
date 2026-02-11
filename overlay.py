"""Vertical Sidebar Overlay for 32+ skills."""

import time
from typing import List, Optional

import cv2
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QScreen, QIcon, QImage, QPixmap, QCursor
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout, QHBoxLayout, QSizeGrip


class ResizeGrip(QWidget):
    """Custom Resize Grip for frameless window."""
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setStyleSheet("background: transparent;")
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 100))
        # Draw a triangle of dots or lines
        painter.drawEllipse(10, 10, 4, 4)
        painter.drawEllipse(15, 5, 4, 4)
        painter.drawEllipse(15, 15, 4, 4)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent().windowHandle().startSystemResize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge)



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
    scale_changed_by_resize = pyqtSignal(float) # Signal to update config when resized via mouse

    def __init__(self, slots: List[dict], config: dict) -> None:
        super().__init__()
        self.config = config
        self.config_path = "config.json" # Should be passed in but simplifying for now, used in save_position
        self._scale = config.get("overlay_scale", 1.0)
        self._slots = slots
        self._orientation = config.get("orientation", "vertical")
        self._locked = config.get("locked", False)

        
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

        # Resize Grip
        self.grip = ResizeGrip(self)
        self.grip.raise_()

        self.widgets: dict[str, SkillWidget] = {}
        
        self.rebuild_ui()
        self.update_lock_state()

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
        icon_size = int(80 * self._scale)
        
        # Grid Logic
        count = len(self._slots)
        if self._orientation == "vertical":
            # Vertical: fixed cols (e.g. 2 for > 16, else 1)
            cols = 2 if count > 16 else 1
            for i, slot in enumerate(self._slots):
                w = SkillWidget(slot["name"], i, size=icon_size)
                row = i // cols
                col = i % cols
                self._layout.addWidget(w, row, col)
                self.widgets[slot["name"]] = w
        else:
            # Horizontal: fixed rows (e.g. 2 for > 16, else 1)
            rows = 2 if count > 16 else 1
            for i, slot in enumerate(self._slots):
                w = SkillWidget(slot["name"], i, size=icon_size)
                row = i % rows
                col = i // rows
                self._layout.addWidget(w, row, col)
                self.widgets[slot["name"]] = w
        
        self.adjustSize()
        # Ensure grip is at bottom right
        self.grip.move(self.width() - 20, self.height() - 20)


    def set_scale(self, scale: float) -> None:
        """Update scale and rebuild UI."""
        if abs(scale - self._scale) > 0.01:
            self._scale = scale
            self.rebuild_ui()

    def set_orientation(self, orientation: str) -> None:
        if orientation != self._orientation:
            self._orientation = orientation
            self.rebuild_ui()

    def set_locked(self, locked: bool) -> None:
        if locked != self._locked:
            self._locked = locked
            self.update_lock_state()

    def update_lock_state(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._locked)
        if self._locked:
            self.grip.hide()
            # If locked, we need to pass mouse events through.
            # WA_TransparentForMouseEvents does exactly that.
            # self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True) # Alternative
        else:
            self.grip.show()
            # self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, False)
        
        # Need to show/hide to refresh attributes sometimes?
        # self.show()


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

    def resizeEvent(self, event) -> None:
        self.grip.move(self.width() - 20, self.height() - 20)
        
        # Live Scaling logic
        # If we are resizing via the grip, we want to update the scale.
        # But we must be careful not to create a feedback loop with adjustSize().
        # Actually, if the user drags the window, the layout will try to stretch widgets.
        # Since SkillWidgets are FixedSize, they won't stretch.
        # So we need to detect the new size and calculate what the scale SHOULD be to fit.
        
        # Simpler approach: 
        # 1. User drags window -> resizeEvent
        # 2. Calculate new scale based on height/width change?
        # A bit complex because of grid constraints.
        
        # Alternative:
        # Just let the grip resize call adjustSize() effectively? No.
        
        # Let's say user drags window to 200% size.
        # We want to increase scale until content fits approximately that size.
        # This is tricky with discrete steps.
        
        # For now, let's keep the grip for moving (handled by system resize) 
        # but implementing "live scaling" cleanly is hard without relayout loop.
        
        # "Dynamic Scaling: As the window is dragged larger or smaller, use scaled() logic to resize"
        
        # If we use startSystemResize, the OS handles the rect.
        # Then we get resizeEvent.
        # Inside resizeEvent, we can check if the size change warrants a scale change.
        
        # Let's try to infer scale from width (if horizontal) or height (if vertical).
        # We know: size = icon_size * count + margins
        # icon_size = int(80 * scale)
        
        # This effectively ignores the resize attempt and snaps to the nearest scale?
        # Or we update scale and rebuild?
        pass

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.save_position()
            event.accept()

            # If we were resizing (how do we know? SystemResize handles it),
            # actually we don't receive mouse events during system resize usually.
            # But after resize, we might want to snap?


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


