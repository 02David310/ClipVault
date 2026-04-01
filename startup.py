import subprocess
import sys
import os


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

PYTHONW = sys.executable.replace("python.exe", "pythonw.exe")

subprocess.Popen(
    [PYTHONW, os.path.join(PROJECT_DIR, "watcher.py")],
    cwd=PROJECT_DIR
)

subprocess.Popen(
    [PYTHONW, os.path.join(PROJECT_DIR, "app.py")],
    cwd=PROJECT_DIR
)

print("Both started!")