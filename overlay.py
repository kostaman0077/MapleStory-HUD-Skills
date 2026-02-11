"""Floating Overlay System for Skills."""

import time
import cv2
from typing import List, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QObject
from PyQt6.QtGui import QColor, QImage, QPixmap, QPainter, QCursor, QAction
from PyQt6.QtWidgets import QWidget, QLabel, QMenu, QApplication

from vision import SkillState
# We will emit signals for saving config, so we don't strictly need save_config here if main handles it.
# But for simplicity, let the manager or window emit a "config_changed" signal.

class SkillWindow(QWidget):
    """Independent floating window for a single skill."""

    # Signals
    position_changed = pyqtSignal(int, int, int) # index, x, y
    open_settings = pyqtSignal()
    request_exit = pyqtSignal()
    
    def __init__(self, slot_index: int, config: dict):
        super().__init__()
        self.slot_index = slot_index
        self.config = config # Reference to the specific slot config dict
        
        self._name = config.get("name", f"Skill {slot_index}")
        self._scale = 1.0 # Will be set by manager
        self._locked = False
        
        # UI State
        self.on_cooldown = False
        self.started_at = 0.0
        
        # Window setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Layout / Widgets
        self.image_label = QLabel(self)
        self.image_label.setScaledContents(True)
        
        self.overlay_label = QLabel(self)
        self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay_label.hide() # Hidden by default (text removed in Phase 5)

        # Draggable state
        self._dragging = False
        self._drag_start_pos = QPoint()

        # Initial Position
        x = config.get("overlay_x", 0)
        y = config.get("overlay_y", 0)
        # If 0,0 maybe default to a row? Manager handles initial placement if needed, 
        # but here we just take what's in config.
        self.move(x, y)

    def set_scale(self, scale: float):
        self._scale = scale
        size = int(80 * scale)
        self.setFixedSize(size, size)
        self.image_label.setGeometry(0, 0, size, size)
        self.overlay_label.setGeometry(0, 0, size, size)
        
        font_size = int(size * 0.4)
        self.overlay_label.setStyleSheet(f"color: white; font-weight: bold; font-size: {font_size}px; background: transparent; border: none;")

    def set_locked(self, locked: bool):
        self._locked = locked
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, locked)

    def update_state(self, state: SkillState):
        # 1. Image
        if state.image is not None and state.image.size > 0:
            h, w, ch = state.image.shape
            bytes_per_line = ch * w
            rgb = cv2.cvtColor(state.image, cv2.COLOR_BGR2RGB)
            q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)

            if state.on_cooldown:
                # Apply Gray Filter
                painter = QPainter(pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                painter.fillRect(pixmap.rect(), QColor(50, 50, 50, 150))
                painter.end()
            
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.clear()

        # 2. Text (Timer) - kept hidden as per Phase 5 request, but logic remains if needed later
        self.overlay_label.hide()
        
    # --- Dragging ---
    def mousePressEvent(self, event):
        if not self._locked and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            # Save position
            pos = self.pos()
            self.config["overlay_x"] = pos.x()
            self.config["overlay_y"] = pos.y()
            self.position_changed.emit(self.slot_index, pos.x(), pos.y())
            event.accept()

    def contextMenuEvent(self, event):
        if self._locked:
            return
        menu = QMenu(self)
        action_settings = menu.addAction("Settings")
        menu.addSeparator()
        action_exit = menu.addAction("Exit App")
        
        action = menu.exec(event.globalPos())
        
        if action == action_settings:
            self.open_settings.emit()
        elif action == action_exit:
            self.request_exit.emit()


class OverlayManager(QObject):
    """Manages multiple SkillWindows."""
    
    open_settings = pyqtSignal()
    config_changed = pyqtSignal() # Emitted when positions change
    request_exit = pyqtSignal()
    
    def __init__(self, slots: List[dict], config: dict):
        super().__init__()
        self.config = config
        self.slots = slots
        self.windows: List[SkillWindow] = []
        
        self.scale = config.get("overlay_scale", 1.0)
        self.locked = config.get("locked", False)
        
        self.rebuild_windows()

    def rebuild_windows(self):
        # Close existing
        for w in self.windows:
            w.close()
            w.deleteLater()
        self.windows.clear()
        
        # Create new
        for i, slot in enumerate(self.slots):
            w = SkillWindow(i, slot)
            w.set_scale(self.scale)
            w.set_locked(self.locked)
            
            # Connect signals
            w.position_changed.connect(self._on_window_moved)
            w.open_settings.connect(self.open_settings.emit)
            w.request_exit.connect(self.request_exit.emit)
            
            w.show()
            self.windows.append(w)
            
            # Initial placement if not set
            if "overlay_x" not in slot:
                # Default grid placement to avoid stacking
                # Simple row for now: 100 + i*100
                x = 100 + (i * int(80 * self.scale + 10))
                y = 100
                slot["overlay_x"] = x
                slot["overlay_y"] = y
                w.move(x, y)

    def update_slots(self, slots: List[dict]):
        self.slots = slots
        self.rebuild_windows()

    def update_config(self, config: dict):
        """Update full configuration."""
        self.config = config
        self.update_slots(config.get("slots", []))
        # We could also update scale/lock if they changed in config, 
        # but those usually come via specific signals.
        # Just in case:
        if "overlay_scale" in config:
            self.set_scale(config["overlay_scale"])
        if "locked" in config:
            self.set_locked(config["locked"])

    def update_skills(self, states: List[SkillState]):
        for st in states:
            # Find window by name? Or index? 
            # Vision logic returns list of SkillState, potentially corresponding to slots index
            # But SkillState has 'name'. 
            # Let's map name to window
            for w in self.windows:
                if w._name == st.name:
                    w.update_state(st)

    def set_scale(self, scale: float):
        self.scale = scale
        self.config["overlay_scale"] = scale
        for w in self.windows:
            w.set_scale(scale)

    def set_locked(self, locked: bool):
        self.locked = locked
        self.config["locked"] = locked
        for w in self.windows:
            w.set_locked(locked)
    
    def close(self):
        for w in self.windows:
            w.close()

    def _on_window_moved(self, index, x, y):
        # Config inside slot dict is already updated by reference
        # Emit generic change signal
        self.config_changed.emit()

    # Proxy methods for main.py compatibility
    def show(self):
        for w in self.windows:
            w.show()

    def hide(self):
        for w in self.windows:
            w.hide()

    def raise_(self):
        for w in self.windows:
            w.raise_()

    def activateWindow(self):
        # Activate the first one?
        if self.windows:
            self.windows[0].activateWindow()
