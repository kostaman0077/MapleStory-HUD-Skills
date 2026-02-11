from PyQt6.QtCore import Qt
try:
    print(f"Qt.Edge: {Qt.Edge}")
    for e in Qt.Edge:
        print(f"  {e.name} = {e.value}")
except AttributeError:
    print("Qt.Edge not found")

try:
    print(f"Qt.BottomRightEdge: {Qt.BottomRightEdge}")
except AttributeError:
    print("Qt.BottomRightEdge not found")
