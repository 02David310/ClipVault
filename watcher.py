import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import folder_uploader
import sys
import socket
from PIL import Image, ImageDraw
import pystray

# Setup logging
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(BASE_DIR, relative_path)

LOG_FILE = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ClipVault', 'watcher.log')
handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5)
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_info(msg):
    logging.info(msg)
    print(msg)

# Prevent multiple instances from running
try:
    # Create a dummy socket to act as a lock
    _instance_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _instance_lock.bind(('127.0.0.1', 47293))
except socket.error:
    # Another instance is already holding the port
    sys.exit(0)

load_dotenv(os.path.join(BASE_DIR, ".env"))
WATCH_FOLDER = os.getenv("WATCH_FOLDER", r"C:\Users\botow\Videos\NVIDIA")

def create_image():
    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        try:
            return Image.open(icon_path)
        except Exception:
            pass
    
    # Erstellt ein transparentes Fallback-Icon mit Branding-Farben
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    # C in Weiß, V in Rot
    d.text((15, 20), "C", fill="#ffffff")
    d.text((35, 20), "V", fill="#cc0000")
    return image

def on_quit(icon, item):
    log_info("Stopping watcher via tray...")
    icon.stop()
    os._exit(0)

def open_dashboard(icon, item):
    # Versuche die lokale GUI EXE zu starten, falls vorhanden
    gui_path = os.path.join(BASE_DIR, "ClipVault.exe")
    if os.path.exists(gui_path):
        import subprocess
        subprocess.Popen([gui_path])
    else:
        import webbrowser
        webbrowser.open("https://clipvault-4s2f.onrender.com")

def setup_tray():
    menu = pystray.Menu(
        pystray.MenuItem("Dashboard öffnen", open_dashboard),
        pystray.MenuItem("Beenden", on_quit)
    )
    icon = pystray.Icon("ClipVault", create_image(), "ClipVault Watcher", menu)
    icon.run()

class ClipHandler(FileSystemEventHandler):
    def __init__(self):
        self.processing = set()

    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".mp4"):
            return
        
        # Normalize path to avoid duplicates from different path formats
        path = os.path.normpath(event.src_path)
        
        if path in self.processing:
            log_info(f"Already processing: {os.path.basename(path)}, skipping")
            return
        
        self.processing.add(path)
        log_info(f"New clip detected: {path}")
        thread = threading.Thread(target=self.handle_clip, args=[path])
        thread.start()

    def handle_clip(self, file_path):
        last_size = -1
        while True:
            current_size = os.path.getsize(file_path)
            if current_size == last_size:
                break
            last_size = current_size
            time.sleep(2)
        
        log_info(f"Uploading: {file_path}")
        folder_uploader.upload_single(file_path)
        self.processing.discard(file_path)

if not os.path.exists(WATCH_FOLDER):
    log_info(f"Creating watch folder: {WATCH_FOLDER}")
    os.makedirs(WATCH_FOLDER, exist_ok=True)

observer = Observer()
observer.schedule(ClipHandler(), path=WATCH_FOLDER, recursive=True)
observer.start()

log_info(f"Watching folder: {WATCH_FOLDER}")

# Starte Tray in einem eigenen Thread, damit der Observer weiterläuft
tray_thread = threading.Thread(target=setup_tray, daemon=True)
tray_thread.start()

while True:
    time.sleep(1)