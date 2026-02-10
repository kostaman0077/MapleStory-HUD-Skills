"""Smoke tests for SkillDetector (brightness mode)."""

import numpy as np
from vision import SkillDetector, SkillState


def _make_bar(slot_w: int = 50, slot_h: int = 50, slot_count: int = 4,
              bright_indices: set | None = None) -> list[np.ndarray]:
    """Create synthetic skill-bar crops.

    ``bright_indices`` — set of slot indices that should be bright (ready).
    All other slots will be dark (on cooldown).
    """
    if bright_indices is None:
        bright_indices = set()

    crops = []
    for i in range(slot_count):
        val = 200 if i in bright_indices else 40  # bright vs dark
        # Create single crop
        crop = np.full((slot_h, slot_w, 3), val, dtype=np.uint8)
        crops.append(crop)
    return crops


def _make_slots(slot_w: int = 50, slot_h: int = 50, count: int = 4):
    return [
        {"name": f"S{i+1}", "x": i * slot_w, "y": 0, "w": slot_w, "h": slot_h}
        for i in range(count)
    ]


def test_all_on_cooldown():
    slots = _make_slots()
    detector = SkillDetector(slots, threshold=100, mode="brightness")
    crops = _make_bar(bright_indices=set())  # all dark
    states = detector.detect_all(crops)
    assert len(states) == 4
    for s in states:
        assert s.on_cooldown is True, f"{s.name} should be on cooldown"


def test_all_ready():
    slots = _make_slots()
    detector = SkillDetector(slots, threshold=100, mode="brightness")
    crops = _make_bar(bright_indices={0, 1, 2, 3})  # all bright
    states = detector.detect_all(crops)
    for s in states:
        assert s.on_cooldown is False, f"{s.name} should NOT be on cooldown"


def test_mixed():
    """Slots 0 and 2 are bright (ready); slots 1 and 3 are dark (cooldown)."""
    slots = _make_slots()
    detector = SkillDetector(slots, threshold=100, mode="brightness")
    crops = _make_bar(bright_indices={0, 2})
    states = detector.detect_all(crops)

    assert states[0].on_cooldown is False  # bright
    assert states[1].on_cooldown is True   # dark
    assert states[2].on_cooldown is False  # bright
    assert states[3].on_cooldown is True   # dark


if __name__ == "__main__":
    test_all_on_cooldown()
    test_all_ready()
    test_mixed()
    print("All tests passed!")
