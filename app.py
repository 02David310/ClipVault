import os
print(f"EXE DIR: {os.path.dirname(__file__)}")
print(f"ENV FILE EXISTS: {os.path.exists(os.path.join(os.path.dirname(__file__), '.env'))}")
from flask import Flask, render_template, jsonify, Response, redirect, session, url_for, request
import queue
import threading
import json
import logging
import time
import sys
from dotenv import load_dotenv

# Pfade für PyInstaller korrigieren
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    BASE_DIR = os.path.dirname(sys.executable)
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__)

load_dotenv(os.path.join(BASE_DIR, ".env"))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_123")
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

log_queue = queue.Queue()

SESSION_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ClipVault')
SESSION_FILE = os.path.join(SESSION_DIR, 'session.json')

def save_session_to_disk(user_data):
    try:
        os.makedirs(SESSION_DIR, exist_ok=True)
        with open(SESSION_FILE, 'w') as f:
            json.dump(user_data, f)
    except Exception as e:
        logging.error(f"Error saving session: {e}")

def load_session_from_disk():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading session: {e}")
    return None

@app.before_request
def load_persistent_user():
    if not session.get('user'):
        user_data = load_session_from_disk()
        if user_data:
            session['user'] = user_data

def get_supabase():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")  # fix here
    return create_client(url, key)

def get_flow():
    from google_auth_oauthlib.flow import Flow
    if getattr(sys, 'frozen', False):
        secrets_path = os.path.join(sys._MEIPASS, "client_secrets.json")
    else:
        secrets_path = os.path.join(BASE_DIR, "client_secrets.json")
    redirect_uri = "http://127.0.0.1:5005/callback"
    if request.host and "127.0.0.1" not in request.host and "localhost" not in request.host:
        redirect_uri = "https://clipvault-4s2f.onrender.com/callback"
    flow = Flow.from_client_secrets_file(
        secrets_path,
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'],
        redirect_uri=redirect_uri
    )
    return flow

@app.route("/")
def home():
    if not session.get('user'):
        return redirect('/login')
    return render_template("dashboard.html")

@app.route("/login")
def login():
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        prompt='consent',
        code_challenge_method='S256'
    )
    session['oauth_state'] = state
    session['code_verifier'] = flow.code_verifier
    session.modified = True
    return redirect(auth_url)

@app.route("/callback")
def callback():
    if 'code' not in request.args:
        return redirect('/login')
    flow = get_flow()
    flow.code_verifier = session.get('code_verifier')
    authorization_response = request.url
    if "localhost" not in request.url:
        authorization_response = authorization_response.replace('http://', 'https://')
    import google.auth.transport.requests
    import google.oauth2.id_token
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    request_session = google.auth.transport.requests.Request()
    time.sleep(2)
    id_info = google.oauth2.id_token.verify_oauth2_token(
        credentials.id_token, request_session, clock_skew_in_seconds=10
    )
    session['user'] = {
        'email': id_info['email'],
        'name': id_info.get('name', id_info['email'])
    }
    save_session_to_disk(session['user'])
    return redirect('/')

@app.route("/logout")
def logout():
    session.clear()
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception as e:
            logging.error(f"Error removing session file: {e}")
    return redirect('/login')

@app.route("/api/client-secrets")
def client_secrets():
    secrets = os.environ.get("GOOGLE_CLIENT_SECRETS_DESKTOP")
    if not secrets:
        return jsonify({"error": "not found"}), 404
    return jsonify(json.loads(secrets))

@app.route("/api/setup-config")
def setup_config():
    email = request.args.get("email")
    secret = request.args.get("secret")
    if not email or not secret:
        return jsonify({"error": "unauthorized"}), 401
    try:
        return jsonify({
            "supabase_url": os.environ.get("SUPABASE_URL"),
            "supabase_key": os.environ.get("SUPABASE_SECRET_KEY"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/api/config")
def get_config():
    if not session.get('user'):
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({
        "supabase_url": os.environ.get("SUPABASE_URL"),
        "supabase_key": os.environ.get("SUPABASE_SECRET_KEY"),
    })

@app.route("/api/clips")
def get_clips():
    if not session.get('user'):
        return jsonify([])
    sb = get_supabase()
    user_email = session['user']['email']
    response = sb.table("clips").select("*").eq("user_id", user_email).execute()
    return jsonify(response.data)

@app.route("/api/me")
def me():
    user = session.get('user')
    if not user:
        return jsonify(None)
    return jsonify(user)

@app.route("/api/sync", methods=["POST"])
def sync():
    import folder_uploader
    threading.Thread(target=folder_uploader.sync_clips).start()
    return jsonify({"status": "syncing"})

@app.route("/logs")
def logs():
    def generate():
        while True:
            log = log_queue.get()
            yield f"data: {log}\n\n"
            if log == "__DONE__":
                break
    return Response(generate(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=False, threaded=True)