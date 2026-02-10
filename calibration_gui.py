"""GUI Calibration Manager for managing 32+ skill slots.

Allows users to:
1. View a list of configured slots.
2. Add new slots by drawing a region on screen.
3. Remove slots.
4. Save configuration.
"""

from __future__ import annotations

import sys
from typing import Optional, List

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QScreen, QCursor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QMessageBox, QMainWindow, QSlider
)

from config import load_config, save_config


class RegionSelector(QWidget):
    """Semi-transparent overlay for selecting a single screen region."""

    selection_confirmed = pyqtSignal(QRect)
    cancelled = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        
        # Cover specific screen or all screens? For now, primary screen.
        screen: QScreen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        
        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self._rect: Optional[QRect] = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.globalPosition().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._origin:
            self._current = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._origin:
            pass # Wait for confirmation or resizing? 
            # For simplicity, drag-and-release confirms immediately.
            # But let's verify size first.
            rect = QRect(self._origin, event.globalPosition().toPoint()).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.selection_confirmed.emit(rect)
                self.close()
            else:
                self._origin = None
                self._current = None
                self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dim background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # Instructions
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(
            self.rect(), 
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, 
            "\n\nDraw a box around the skill icon. Release to confirm. ESC to cancel."
        )

        # Selection rect
        if self._origin and self._current:
            rect = QRect(self._origin, self._current).normalized()
            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.setBrush(QBrush(QColor(0, 255, 0, 50)))
            painter.drawRect(rect)



class SettingsWindow(QMainWindow):
    """Main window for managing skills and overlay settings."""

    # Signals to notify overlay of changes
    config_changed = pyqtSignal(dict)  # Emits full config
    overlay_scale_changed = pyqtSignal(float)

    def __init__(self, config_path: str = "config.json") -> None:
        super().__init__()
        self.setWindowTitle("Overlay Settings")
        self.resize(500, 600)
        self.config_path = config_path
        self.config = load_config(config_path)
        
        # UI Setup
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- Skill List Section ---
        layout.addWidget(QLabel("<b>Skill Slots</b>"))
        self.slot_list = QListWidget()
        layout.addWidget(self.slot_list)
        
        # Skill Buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add New")
        self.btn_edit = QPushButton("Edit Selected")
        self.btn_remove = QPushButton("Remove")
        self.btn_clear = QPushButton("Clear All")
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        # --- Appearance Section ---
        layout.addSpacing(20)
        layout.addWidget(QLabel("<b>Appearance</b>"))
        
        # Scale Slider
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Overlay Scale:"))
        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(5, 30) # 0.5x to 3.0x
        current_scale = self.config.get("overlay_scale", 1.0)
        self.slider_scale.setValue(int(current_scale * 10))
        scale_layout.addWidget(self.slider_scale)
        self.lbl_scale_val = QLabel(f"{current_scale:.1f}x")
        scale_layout.addWidget(self.lbl_scale_val)
        layout.addLayout(scale_layout)

        # --- Footer ---
        layout.addStretch()
        self.btn_save = QPushButton("Save Config")
        layout.addWidget(self.btn_save)

        # Signals
        self.btn_add.clicked.connect(self.add_skill_flow)
        self.btn_edit.clicked.connect(self.edit_skill_flow)
        self.btn_remove.clicked.connect(self.remove_slot)
        self.btn_clear.clicked.connect(self.clear_all_slots)
        self.btn_save.clicked.connect(self.save_config_file)
        
        self.slider_scale.valueChanged.connect(self.on_scale_changed)
        
        self.refresh_list()

    def refresh_list(self) -> None:
        self.slot_list.clear()
        for i, slot in enumerate(self.config.get("slots", [])):
            name = slot.get("name", f"Skill {i+1}")
            coords = f"x={slot['x']},y={slot['y']} {slot['w']}x{slot['h']}"
            item = QListWidgetItem(f"{name}  [{coords}]")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.slot_list.addItem(item)
        
        # Notify overlay of slot changes
        self.config_changed.emit(self.config)

    def on_scale_changed(self, value: int) -> None:
        scale = value / 10.0
        self.lbl_scale_val.setText(f"{scale:.1f}x")
        self.config["overlay_scale"] = scale
        self.overlay_scale_changed.emit(scale)

    # --- Skill Actions ---

    def add_skill_flow(self) -> None:
        self.selector = RegionSelector()
        self.selector.selection_confirmed.connect(self._on_add_confirmed)
        self.selector.showFullScreen()
        self.hide()

    def _on_add_confirmed(self, rect: QRect) -> None:
        self.show()
        slots = self.config.get("slots", [])
        new_idx = len(slots) + 1
        new_slot = {
            "name": f"Skill {new_idx}",
            "x": rect.x(),
            "y": rect.y(),
            "w": rect.width(),
            "h": rect.height(),
            "enabled": True
        }
        slots.append(new_slot)
        self.config["slots"] = slots
        self.refresh_list()

    def edit_skill_flow(self) -> None:
        row = self.slot_list.currentRow()
        if row < 0:
            return
        
        # Store which row we are editing
        self._editing_row = row
        self.selector = RegionSelector()
        self.selector.selection_confirmed.connect(self._on_edit_confirmed)
        self.selector.showFullScreen()
        self.hide()

    def _on_edit_confirmed(self, rect: QRect) -> None:
        self.show()
        slots = self.config.get("slots", [])
        if 0 <= self._editing_row < len(slots):
            # Update specific fields
            slots[self._editing_row]["x"] = rect.x()
            slots[self._editing_row]["y"] = rect.y()
            slots[self._editing_row]["w"] = rect.width()
            slots[self._editing_row]["h"] = rect.height()
            self.config["slots"] = slots
            self.refresh_list()

    def remove_slot(self) -> None:
        row = self.slot_list.currentRow()
        if row >= 0:
            slots = self.config.get("slots", [])
            if 0 <= row < len(slots):
                del slots[row]
                self.config["slots"] = slots
                self.refresh_list()

    def clear_all_slots(self) -> None:
        if QMessageBox.question(self, "Confirm", "Clear all skills?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.config["slots"] = []
            self.refresh_list()

    def save_config_file(self) -> None:
        save_config(self.config_path, self.config)
        print(f"[settings] Saved config.")


def run_gui(config_path: str = "config.json"):
    app = QApplication.instance() or QApplication(sys.argv)
    window = SettingsWindow(config_path)
    window.show()
    app.exec()

if __name__ == "__main__":
    run_gui()

