"""Game HUD Overlay — main entry point.

Usage
-----
  python main.py              # run the overlay
  python main.py --calibrate  # launch calibration manager
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List


from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QMutex, QPoint
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from capture import ScreenCapture
from config import load_config
from overlay import SidebarOverlay
from vision import SkillDetector, SkillState
from calibration_gui import SettingsWindow


class CaptureWorker(QThread):
    """Runs the grab -> crop -> parallel detect loop."""

    skills_updated = pyqtSignal(list)

    def __init__(
        self,
        capture: ScreenCapture,
        detector: SkillDetector,
        fps: int = 30,
        max_workers: int = 4
    ) -> None:
        super().__init__()
        self._capture = capture
        self._detector = detector
        self._interval = 1.0 / max(fps, 1)
        self._running = True
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._mutex = QMutex()

    @pyqtSlot(dict)
    def update_config(self, config: dict) -> None:
        """Update slots safely."""
        slots = config.get("slots", [])
        self._mutex.lock()
        try:
            self._capture.update_slots(slots)
            self._detector.update_slots(slots)
        finally:
            self._mutex.unlock()

    def run(self) -> None:
        frame_count = 0
        t0 = time.monotonic()

        while self._running:
            tick_start = time.monotonic()

            # 1. Grab & Crop (Protected)
            self._mutex.lock()
            try:
                crops = self._capture.grab_slots()
                # Snapshot detector slots to ensure length match during iteration
                # We assume detector.slots and capture.slots are synchronized in update_config
                current_slots = list(self._detector.slots) # Shallow copy list
            finally:
                self._mutex.unlock()
            
            if not crops:
                # No slots defined or capture failed
                time.sleep(1.0)
                continue

            # 2. Parallel Analysis
            futures = []
            
            # Submit tasks
            for i, crop in enumerate(crops):
                if crop is None or i >= len(current_slots):
                    continue
                name = current_slots[i]["name"]
                futures.append(self._executor.submit(self._detector.detect_one, name, crop))

            # Collect results (blocking)
            states = [f.result() for f in futures]
            
            self.skills_updated.emit(states)

            # (Telemetry code omitted for brevity but could trigger every 5s)
            
            # throttle
            elapsed = time.monotonic() - tick_start
            sleep_time = self._interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> None:
        self._running = False
        self._executor.shutdown(wait=False)
        self.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description="32-Slot Skills Tracker")
    parser.add_argument(
        "--config", default="config.json",
        help="Path to configuration file",
    )
    # Kept for backward compat / shortcut, but now opens settings AND overlay
    parser.add_argument(
        "--calibrate", action="store_true",
        help="Open the Settings window on launch",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running if settings closed

    cfg = load_config(args.config)
    slots = cfg.get("slots", [])
    
    # Core objects
    capture = ScreenCapture(slots)
    detector = SkillDetector(
        slots=slots,
        threshold=cfg.get("brightness_threshold", 100),
        mode=cfg.get("detection_mode", "brightness"),
        template_dir=cfg.get("template_dir", "templates"),
    )

    # Windows
    # 1. Overlay
    overlay = SidebarOverlay(slots, config=cfg)
    
    # Restore position if saved
    if "window_x" in cfg and "window_y" in cfg:
        overlay.move(cfg["window_x"], cfg["window_y"])
    
    # --- VISIBILITY CHECK ---
    # Ensure overlay is on-screen. If not, reset to default.
    # We check if the window geometry intersects with any screen's available geometry.
    # Since it's a frameless tool window, we might need to be careful.
    # Simple check: is the top-left corner within any screen?
    overlay_visible = False
    for screen in QApplication.screens():
        if screen.availableGeometry().contains(overlay.geometry()):
            overlay_visible = True
            break
    
    if not overlay_visible:
        print("[main] Overlay detected off-screen or invalid. Resetting position.")
        # Reset to top-right of primary screen
        primary = QApplication.primaryScreen().availableGeometry()
        # Default to right side
        overlay.move(primary.width() - overlay.width() - 50, 100)

    overlay.show()

    # --- SYSTEM TRAY ---
    tray_icon = QSystemTrayIcon(app)
    # Use a standard icon since we might not have a custom one
    tray_icon.setIcon(app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon))
    
    tray_menu = QMenu()
    action_show = QAction("Show Overlay", tray_menu)
    action_settings = QAction("Settings", tray_menu)
    action_quit = QAction("Quit", tray_menu)

    tray_menu.addAction(action_show)
    tray_menu.addAction(action_settings)
    tray_menu.addSeparator()
    tray_menu.addAction(action_quit)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()


    # 2. Settings
    settings = SettingsWindow(args.config)
    if args.calibrate or not slots:
        settings.show()

    # Worker
    worker = CaptureWorker(
        capture, 
        detector, 
        fps=cfg.get("capture_fps", 30),
        max_workers=8
    )

    # Connections
    # Overlay -> Settings
    overlay.open_settings.connect(settings.show)
    
    # Settings -> Overlay & Worker
    settings.config_changed.connect(lambda c: overlay.update_slots(c.get("slots", [])))
    settings.config_changed.connect(worker.update_config)
    
    settings.overlay_scale_changed.connect(overlay.set_scale)
    settings.orientation_changed.connect(overlay.set_orientation)
    settings.locked_changed.connect(overlay.set_locked)
    
    # Sync resize back to settings
    overlay.scale_changed_by_resize.connect(settings.update_scale_from_overlay)

    # Tray Connections
    action_show.triggered.connect(overlay.show)
    action_show.triggered.connect(overlay.raise_)
    action_show.triggered.connect(overlay.activateWindow)
    action_settings.triggered.connect(settings.show)
    action_quit.triggered.connect(app.quit)

    # Double-click tray to open settings
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            settings.show()
    tray_icon.activated.connect(on_tray_activated)


    # Worker -> Overlay
    worker.skills_updated.connect(overlay.update_skills)
    
    worker.start()

    print(f"[main] App started. Right-click overlay for settings.")

    try:
        exit_code = app.exec()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        worker.stop()
        capture.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
