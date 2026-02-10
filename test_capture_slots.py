"""Unit test for multi-slot capture logic."""

import numpy as np
from capture import ScreenCapture

def test_capture_slots():
    # Define 3 disjoint slots
    slots = [
        {"name": "S1", "x": 100, "y": 100, "w": 50, "h": 50},
        {"name": "S2", "x": 200, "y": 100, "w": 50, "h": 50},
        {"name": "S3", "x": 150, "y": 200, "w": 30, "h": 30},
    ]

    cap = ScreenCapture(slots)
    
    # Check computed bounding box
    # S1 (100,100), S2 (200,100), S3 (150, 200)
    # Box: left=100, top=100
    # Right edge: max(100+50, 200+50, 150+30) = 250
    # Bottom edge: max(100+50, 100+50, 200+30) = 230
    # Width = 250 - 100 = 150
    # Height = 230 - 100 = 130
    bbox = cap._monitor
    print(f"Bounding box: {bbox}")
    assert bbox["left"] == 100
    assert bbox["top"] == 100
    assert bbox["width"] == 150
    assert bbox["height"] == 130

    # Test grab
    crops = cap.grab_slots()
    assert len(crops) == 3
    
    # Check shapes
    assert crops[0].shape == (50, 50, 3)
    assert crops[1].shape == (50, 50, 3)
    assert crops[2].shape == (30, 30, 30) or crops[2].shape == (30, 30, 3) 
    # mss returns 3 channels if we slice [:,:,:3] correctly
    
    print("Capture test passed!")
    cap.close()

if __name__ == "__main__":
    test_capture_slots()
