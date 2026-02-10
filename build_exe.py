
import PyInstaller.__main__
import os
import shutil

def build():
    print("Building Skill Tracker...")
    
    # Clean previous build
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")

    # PyInstaller arguments
    args = [
        "main.py",                         # Script to package
        "--name=SkillTracker",             # Executable name
        "--windowed",                      # No console window
        "--noconfirm",                     # Overwrite output
        "--onedir",                        # Generate directory settings
        "--clean",
        # "--add-data=templates;templates", # Uncomment if needed
    ]

    PyInstaller.__main__.run(args)
    
    # Post-build: Copy config and templates
    dist_dir = os.path.join("dist", "SkillTracker")
    if os.path.exists("config.json"):
        shutil.copy("config.json", os.path.join(dist_dir, "config.json"))
        print("Copied config.json")
    
    if os.path.exists("templates"):
        dest_templates = os.path.join(dist_dir, "templates")
        if os.path.exists(dest_templates):
            shutil.rmtree(dest_templates)
        shutil.copytree("templates", dest_templates)
        print("Copied templates folder")
    
    print("Build complete. Check 'dist/SkillTracker'")

if __name__ == "__main__":
    build()
