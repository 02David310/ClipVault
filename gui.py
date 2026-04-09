import sys
import os
import traceback
import time
import socket
import threading

DEBUG_LOG = os.path.join(os.environ.get('TEMP', '.'), "clipvault_debug.log")

def log_debug(msg):
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
    except:
        pass

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def global_exception_handler(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    log_debug(f"FATAL ERROR:\n{err_msg}")

sys.excepthook = global_exception_handler

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(get_base_dir(), relative_path)

def ensure_icon():
    from PIL import Image, ImageDraw
    icon_path = get_resource_path("icon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(os.environ.get("TEMP", "."), "cv_fallback.png")
        if not os.path.exists(icon_path):
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            try:
                d.text((15, 20), "C", fill="#ffffff")
                d.text((35, 20), "V", fill="#cc0000")
                img.save(icon_path)
            except Exception:
                return None
    return icon_path

def start_flask():
    try:
        log_debug("Flask: Importing app...")
        from app import app
        log_debug("Flask: Starting app.run on 127.0.0.1:5005...")
        app.run(host='127.0.0.1', port=5005, debug=False, threaded=True)
    except Exception:
        log_debug(f"Flask: CRITICAL ERROR: {traceback.format_exc()}")

def wait_for_flask():
    log_debug("Polling Flask port 5005 via socket...")
    for i in range(60):
        try:
            with socket.create_connection(("127.0.0.1", 5005), timeout=0.5):
                log_debug(f"Flask port open after {i * 0.5:.1f}s.")
                time.sleep(0.5)
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
    log_debug("Flask port failed to open after 30 seconds.")
    return False

def main():
    log_debug("--- GUI Startup Process Started ---")
    try:
        import webview

        log_debug("Starting Flask thread...")
        server_thread = threading.Thread(target=start_flask, daemon=True)
        server_thread.start()

        if not wait_for_flask():
            log_debug("Aborting: Flask port never opened.")
            return

        log_debug("Initializing webview window...")
        webview.create_window(
            'ClipVault',
            'http://127.0.0.1:5005',
            background_color='#1a1a1a',
            width=1200,
            height=800
            
        )

        log_debug("Launching webview.start()...")
        webview.start()

    except Exception:
        log_debug(f"Exception in main: {traceback.format_exc()}")

if __name__ == "__main__":
    main()