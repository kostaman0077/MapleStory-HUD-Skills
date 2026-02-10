"""High-speed screen capture using mss with multi-slot support."""

import mss
import numpy as np
from typing import List, Dict, Optional


class ScreenCapture:
    """Grabs a screen region covering all slots and crops them.

    Parameters
    ----------
    slots : list[dict]
        List of slot configurations, each with keys x, y, w, h.
    """

    def __init__(self, slots: List[Dict]) -> None:
        self.slots = slots
        self._sct = None
        self._monitor = self._compute_bounding_box(slots)

    def _compute_bounding_box(self, slots: List[Dict]) -> Dict[str, int]:
        """Determine the minimal rectangle containing all slots."""
        if not slots:
            return {"top": 0, "left": 0, "width": 100, "height": 100}

        min_x = min(s["x"] for s in slots)
        min_y = min(s["y"] for s in slots)
        max_x = max(s["x"] + s["w"] for s in slots)
        max_y = max(s["y"] + s["h"] for s in slots)

        return {
            "left": int(min_x),
            "top": int(min_y),
            "width": int(max_x - min_x),
            "height": int(max_y - min_y),
        }

    def update_slots(self, slots: List[Dict]) -> None:
        """Update the list of slots and recompute the bounding box."""
        self.slots = slots
        self._monitor = self._compute_bounding_box(slots)


    def grab_slots(self) -> List[Optional[np.ndarray]]:
        """Capture the screen and return a list of cropped slot images."""
        if not self.slots:
            return []

        if self._sct is None:
            self._sct = mss.mss()

        # Grab the big chunk
        shot = self._sct.grab(self._monitor)
        
        # Convert to numpy (BGRA -> BGR)
        # Note: mss returns BGRA. We drop alpha.
        full_frame = np.array(shot, dtype=np.uint8)[:, :, :3]

        # Crop individual slots
        crops = []
        base_x = self._monitor["left"]
        base_y = self._monitor["top"]

        for s in self.slots:
            # Calculate relative coordinates within the captured frame
            x = s["x"] - base_x
            y = s["y"] - base_y
            w = s["w"]
            h = s["h"]
            
            # Bounds check (just in case)
            if x < 0 or y < 0 or x + w > full_frame.shape[1] or y + h > full_frame.shape[0]:
                crops.append(None) # Should not happen if bounding box is correct
                continue

            crop = full_frame[y : y + h, x : x + w]
            crops.append(crop)

        return crops

    def close(self) -> None:
        if self._sct:
            self._sct.close()
            self._sct = None
