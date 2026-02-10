"""OpenCV-based skill-state detection.

Supports two modes:

* **brightness** (default) — compares mean brightness of each slot to a
  threshold.
* **template** — uses ``cv2.matchTemplate`` against reference PNGs stored
  in a templates directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Dict

import cv2
import numpy as np


@dataclass
class SkillState:
    """Result for a single skill slot."""
    name: str
    on_cooldown: bool
    brightness: float
    match_score: Optional[float] = None
    image: Optional[np.ndarray] = None


class SkillDetector:
    """Detect whether each skill slot is on cooldown.

    Parameters
    ----------
    slots : list[dict]
        List of slot configs (name, etc).
    threshold : float
        Brightness threshold (0-255).
    mode : str
        ``"brightness"`` or ``"template"``.
    template_dir : str
        Directory containing ``<slot_name>.png`` reference images.
    """

    def __init__(
        self,
        slots: List[dict],
        threshold: float = 100.0,
        mode: str = "brightness",
        template_dir: str = "templates",
    ) -> None:
        self.slots = slots
        self.threshold = threshold
        self.mode = mode
        self._templates: Dict[str, np.ndarray] = {}

        if mode == "template":
            self._load_templates(template_dir)
            if not self._templates:
                print("[vision] No templates found — falling back to brightness mode.")
                self.mode = "brightness"

    def update_slots(self, slots: List[dict]) -> None:
        """Update the list of slots."""
        self.slots = slots


    def detect_all(self, crops: List[Optional[np.ndarray]]) -> List[SkillState]:
        """Analyse a list of slot crops and return states."""
        results = []
        for i, crop in enumerate(crops):
            slot = self.slots[i]
            if crop is None or crop.size == 0:
                results.append(SkillState(slot["name"], False, 255.0))
                continue
            
            results.append(self.detect_one(slot["name"], crop))
        return results

    def detect_one(self, name: str, crop: np.ndarray) -> SkillState:
        """Analyse a single slot crop."""
        if self.mode == "template" and name in self._templates:
            return self._detect_template(name, crop)
        return self._detect_brightness(name, crop)

    def _detect_brightness(self, name: str, crop: np.ndarray) -> SkillState:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        return SkillState(
            name=name,
            on_cooldown=mean_brightness < self.threshold,
            brightness=mean_brightness,
            image=crop,
        )

    def _detect_template(self, name: str, crop: np.ndarray) -> SkillState:
        template = self._templates[name]
        # Resize template if needed
        if template.shape[:2] != crop.shape[:2]:
            template = cv2.resize(template, (crop.shape[1], crop.shape[0]))

        result = cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED)
        score = float(result.max())
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))

        # A low match score combined with low brightness => cooldown
        on_cooldown = score < 0.6 and mean_brightness < self.threshold
        return SkillState(
            name=name,
            on_cooldown=on_cooldown,
            brightness=mean_brightness,
            match_score=score,
            image=crop,
        )

    def _load_templates(self, template_dir: str) -> None:
        if not os.path.isdir(template_dir):
            return
        for slot in self.slots:
            name = slot["name"]
            # Try exact name, or safe filename
            safe_name = "".join(x for x in name if x.isalnum() or x in " _-")
            path = os.path.join(template_dir, f"{safe_name}.png")
            
            if os.path.isfile(path):
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is not None:
                    self._templates[name] = img
