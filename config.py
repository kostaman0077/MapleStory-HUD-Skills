"""Configuration read/write helpers."""

import json
import os

DEFAULT_CONFIG = {
    "capture_fps": 30,
    "brightness_threshold": 100,
    "sidebar_position": "right",  # "left" or "right"
    "overlay_scale": 1.0,
    "detection_mode": "brightness",
    "template_dir": "templates",
    "orientation": "vertical",  # "vertical" or "horizontal"
    "locked": False,
    "slots": [],  # List of dicts: {name, x, y, w, h, enabled, default_cooldown}
}


def load_config(path: str = "config.json") -> dict:
    """Load configuration from *path*, falling back to defaults for missing keys."""
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                user = json.load(fh)
            config.update(user)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[config] Error loading {path}: {e}")
    
    # Ensure slots is a list
    if not isinstance(config.get("slots"), list):
        config["slots"] = []
        
    return config


def save_config(path: str, data: dict) -> None:
    """Persist *data* to *path* as pretty-printed JSON."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
