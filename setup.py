import os
import sys
import subprocess
import webbrowser
import threading
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

print("=== ClipVault Setup ===\n")

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
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secrets.json"),
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
script_dir = os.path.dirname(os.path.abspath(__file__))
token_path = os.path.join(script_dir, "token.json")
with open(token_path, "w") as f:
    f.write(creds.to_json())

# Get user email from token
import google.oauth2.id_token
import google.auth.transport.requests
request_session = google.auth.transport.requests.Request()
id_info = google.oauth2.id_token.verify_oauth2_token(
    creds.id_token, request_session
)
email = id_info['email']
print(f"\nLogged in as: {email}")

# Fetch config from Render
print("Fetching config...")
# We use a simple token approach - user visits site to get their token
config_response = requests.get(
    "https://clipvault-4s2f.onrender.com/api/setup-config",
    params={"email": email, "secret": creds.token}
)
config = config_response.json()

# Save .env
env_path = os.path.join(script_dir, ".env")
with open(env_path, "w") as f:
    f.write(f"SUPABASE_URL={config['supabase_url']}\n")
    f.write(f"SUPABASE_SECRET_KEY={config['supabase_key']}\n")
    f.write(f"CLIPVAULT_USER_ID={email}\n")
    f.write(f"WATCH_FOLDER={nvidia_folder}\n")

print("Config saved!")

# Update watcher WATCH_FOLDER
watcher_path = os.path.join(script_dir, "watcher.py")
with open(watcher_path, "r") as f:
    content = f.read()
content = content.replace(
    'WATCH_FOLDER = "C:/Users/botow/Videos/NVIDIA"',
    f'WATCH_FOLDER = r"{nvidia_folder}"'
)
with open(watcher_path, "w") as f:
    f.write(content)

# Task Scheduler
pythonw = sys.executable.replace("python.exe", "pythonw.exe")
subprocess.run([
    "schtasks", "/create",
    "/tn", "ClipVault",
    "/tr", f'"{pythonw}" "{watcher_path}"',
    "/sc", "onlogon",
    "/rl", "highest",
    "/f"
], shell=True)

print("\n✓ Setup complete! ClipVault will start automatically on next login.")
input("\nPress Enter to exit...")