import os
import sys
import subprocess
import webbrowser
import threading
import json
import requests
import winreg
import ctypes
import shutil
import time
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow

# Erlaube HTTP für den lokalen Google-Login (notwendig für localhost)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Request Admin privileges
if not is_admin():
    print("Requesting administrator privileges...")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

print("=== ClipVault Setup ===\n")

# Define Installation Directory
INSTALL_DIR = os.path.join(os.environ['LOCALAPPDATA'], "ClipVault")
if not os.path.exists(INSTALL_DIR):
    os.makedirs(INSTALL_DIR)
    print(f"Created installation folder: {INSTALL_DIR}")

script_dir = INSTALL_DIR # Redirect config saves to install dir

# Ask for NVIDIA folder
nvidia_folder = input("Enter your NVIDIA clips folder path (e.g. C:/Users/YourName/Videos/NVIDIA): ").strip('"')
while not os.path.isdir(nvidia_folder):
    print("Folder not found! Try again.")
    nvidia_folder = input("Enter your NVIDIA clips folder path: ").strip('"')

# OAuth via localhost
auth_code = [None]
auth_done = threading.Event()

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if 'code' in params:
            auth_code[0] = self.path
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Login successful! You can close this window.")
            auth_done.set()
        def log_message(self, format, *args):
            pass  # suppress server logs

server = HTTPServer(('localhost', 8765), CallbackHandler)
server_thread = threading.Thread(target=server.handle_request)
server_thread.start()


# Start OAuth flow
flow = Flow.from_client_secrets_file(
    get_resource_path("client_secrets.json"),
    scopes=[
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube'
    ],
    redirect_uri='http://localhost:8765/callback'
)

auth_url, state = flow.authorization_url(prompt='consent')
print("\nOpening browser for Google login...")
webbrowser.open(auth_url)

auth_done.wait(timeout=120)

if not auth_code[0]:
    print("Login timed out! Please try again.")
    sys.exit(1)

# Complete OAuth
flow.fetch_token(authorization_response=f"http://localhost:8765{auth_code[0]}")
creds = flow.credentials

# Save token.json
token_path = os.path.join(script_dir, "token.json")
with open(token_path, "w") as f:
    f.write(creds.to_json())

# Get user email from token
import google.oauth2.id_token
import google.auth.transport.requests
request_session = google.auth.transport.requests.Request()
# Kurze Pause, um minimale Zeitunterschiede zu den Google-Servern auszugleichen
time.sleep(2)
id_info = google.oauth2.id_token.verify_oauth2_token(
    creds.id_token, request_session
)
email = id_info['email']
print(f"\nLogged in as: {email}")

# Fetch config from Render
print("Fetching config from Render (this may take up to 30 seconds if the server is sleeping)...")
try:
    # We use a simple token approach - user visits site to get their token
    config_response = requests.get(
        "https://clipvault-4s2f.onrender.com/api/setup-config",
        params={"email": email, "secret": creds.token},
        timeout=45  # Stop waiting after 45 seconds
    )
    config_response.raise_for_status()  # Raise an error if the server returned a 4xx or 5xx
    config = config_response.json()
except Exception as e:
    print(f"\nError fetching config: {e}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# Save .env
env_path = os.path.join(script_dir, ".env")
with open(env_path, "w") as f:
    f.write(f"SUPABASE_URL={config['supabase_url']}\n")
    f.write(f"SUPABASE_SECRET_KEY={config['supabase_key']}\n")
    f.write(f"CLIPVAULT_USER_ID={email}\n")
    f.write(f"WATCH_FOLDER={nvidia_folder}\n")

print("Config saved!")

# Copy scripts to permanent location
print("Installing scripts...")

# Stop existing processes if they are running
subprocess.run(["taskkill", "/F", "/IM", "ClipVaultWatcher.exe", "/T"], capture_output=True, shell=True)
subprocess.run(["taskkill", "/F", "/IM", "ClipVault.exe", "/T"], capture_output=True, shell=True)
subprocess.run(["taskkill", "/F", "/IM", "ClipVaultUninstall.exe", "/T"], capture_output=True, shell=True)

installed_exes = {}
for exe_name in ["ClipVaultWatcher.exe", "ClipVault.exe", "ClipVaultStatus.exe", "ClipVaultUninstall.exe"]:
    src = get_resource_path(exe_name)
    dst = os.path.join(INSTALL_DIR, exe_name)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"Installed: {exe_name}")
        installed_exes[exe_name] = dst
    else:
        print(f"⚠ Warning: {exe_name} not found in installer package!")

# Create Desktop Shortcut for ClipVault.exe
def get_desktop_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        return winreg.QueryValueEx(key, "Desktop")[0]
    except:
        return os.path.join(os.environ['USERPROFILE'], 'Desktop')

target_exe = installed_exes.get("ClipVault.exe")
if target_exe:
    print("Creating Desktop shortcut...")
    try:
        shortcut_path = os.path.join(get_desktop_path(), "ClipVault.lnk")
        shell_script = f"$s=(New-Object -COM WScript.Shell).CreateShortcut('{shortcut_path}');$s.TargetPath='{target_exe}';$s.WorkingDirectory='{INSTALL_DIR}';$s.IconLocation='{target_exe},0';$s.Save()"
        subprocess.run(["powershell", "-Command", shell_script], capture_output=True, shell=True)
        print("✓ Desktop shortcut created!")
    except Exception as e:
        print(f"Could not create shortcut: {e}")
else:
    print("⚠ Could not create shortcut: ClipVault.exe was not installed correctly.")

# Task Scheduler
watcher_path = installed_exes.get("ClipVaultWatcher.exe")
subprocess.run([
    "schtasks", "/create",
    "/tn", "ClipVault",
    "/tr", f'"{watcher_path}"',
    "/sc", "onlogon",
    "/rl", "highest",
    "/f"
], shell=True)

# Clean up old registry entry if it exists to prevent duplicate startup
try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    winreg.DeleteValue(key, "ClipVault")
    winreg.CloseKey(key)
except FileNotFoundError:
    pass

print("✓ Auto-start configured via Task Scheduler!")

print("\n✓ Setup complete!")

import_choice = input("\nWould you like to import existing clips from your NVIDIA folder now? (y/n): ").lower()
if import_choice == 'y':
    print("Starting import process... This might take a while.")
    # We can import and call the folder_uploader directly since it's part of the source
    import folder_uploader
    folder_uploader.upload_folder(nvidia_folder)
    print("✓ Import complete!")

print("\nClipVault will start automatically on next login.")
input("\nPress Enter to exit...")