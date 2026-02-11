# Skill Tracker Overlay

**A high-performance, customizable overlay for tracking skill cooldowns in any game.**

![Status](https://img.shields.io/badge/status-active-success.svg)
![Platform](https://img.shields.io/badge/platform-windows-blue.svg)

Skill Tracker is a lightweight desktop application that monitors specific regions of your screen (your game's skill bar) and creates a floating overlay. This overlay shows you exactly when your skills are ready, even if you're focused on the action in the center of the screen.

---

## 🚀 Key Features

*   **Real-Time Tracking**: Instantly detects when a skill is on cooldown (darkened) or ready (bright).
*   **Dynamic Overlay**:
    *   **Drag & Drop**: Move the overlay anywhere on your screen.
    *   **Scalable**: Resize the icons to fit your setup ideally.
    *   **Always on Top**: Stays visible over your game window (borderless windowed mode recommended).
*   **Easy Configuration**:
    *   **Visual Setup**: Simply draw a box around your skill icons to add them.
    *   **Live Updates**: Changes in settings appear immediately on the overlay.
*   **Performance**: Optimized for minimal impact on your game's FPS.
<img width="968" height="716" alt="image" src="https://github.com/user-attachments/assets/d9f697a6-aab8-47ed-8cc2-8c4caf62b717" />
<img width="997" height="738" alt="image" src="https://github.com/user-attachments/assets/5f7c5dbd-0150-479c-9386-aca97bbc7b35" />
![Animation](https://github.com/user-attachments/assets/7d77d80a-e623-41d6-9d80-adc55f7846fa)

---

## 📥 Installation

### Option A: Standalone Executable (Recommended)
1.  Navigate to the `dist/SkillTracker` folder.
2.  Run `SkillTracker.exe`.
3.  *No Python installation required.*

### Option B: Run from Source (For Developers)
1.  Install Python 3.10+.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the app:
    ```bash
    python main.py
    ```

---

## 🎮 User Guide

### 1. First Run & Setup
When you first launch the application, you'll see an overlay (likely empty or with default slots) and possibly the **Settings** window.

**To open Settings:**
1.  Find the overlay on your screen.
2.  **Right-Click** on the overlay.
3.  Select **Settings**.

### 2. Adding Skills
1.  Open the **Settings** window.
2.  Click **"Add New"**.
3.  Your screen will freeze slightly, and you'll see a crosshair.
4.  **Click and Drag** to draw a box around a single skill icon in your game.
5.  Release the mouse. The skill is now tracked!
6.  Repeat for as many skills as you want.

### 3. Customizing the Overlay
*   **Move**: Simply **Left-Click and Drag** the overlay window to position it where you want. The position is saved automatically.
*   **Resize**: In the **Settings** window, drag the **Overlay Scale** slider. The icons will grow or shrink in real-time.

### 4. Managing Skills
*   **Edit**: Select a skill in the list and click **"Edit Selected"** to re-draw its detection region.
*   **Remove**: Select a skill and click **"Remove"** to delete it.
*   **Clear All**: Removes all configured skills to start fresh.

---

## 🔧 Troubleshooting

*   **Overlay is Black/Invisible**:
    *   Ensure your game is running in **Windowed** or **Borderless Windowed** mode. Fullscreen exclusive mode may hide desktop overlays.
*   **Skills not detecting correctly**:
    *   Open `config.json` and adjust `"brightness_threshold"` (default is 100). Lower it if skills are detected as "cooldown" too often.
    *   Ensure nothing is blocking the game UI (chat windows, notifications).

---

## 📦 Building from Source

If you want to modify the code and build your own executable:

1.  Make your changes.
2.  Run the build script:
    ```bash
    python build_exe.py
    ```
3.  The new executable will be in `dist/SkillTracker/`.
