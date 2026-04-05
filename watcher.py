import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import folder_uploader

WATCH_FOLDER = r"C:\Users\botow\Videos\NVIDIA"

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
            print(f"Already processing: {os.path.basename(path)}, skipping")
            return
        
        self.processing.add(path)
        print(f"New clip detected: {path}")
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
        
        print(f"Uploading: {file_path}")
        folder_uploader.upload_single(file_path)
        self.processing.discard(file_path)

observer = Observer()
observer.schedule(ClipHandler(), path=WATCH_FOLDER, recursive=True)
observer.start()

print(f"Watching folder: {WATCH_FOLDER}")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()