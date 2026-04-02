from flask import Flask, render_template, jsonify, Response, redirect, session, url_for, request
import queue
import threading
import os
import json
import folder_uploader
import time
from supabase import create_client
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_HTTPONLY'] = True
log_queue = queue.Queue()

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    return create_client(url, key)

@app.route("/")
def home():
    user = session.get('user')
    if not user:
        return redirect('/login')
    return render_template("dashboard.html")

@app.route("/login")
def login():
    return google.authorize_redirect(url_for('callback', _external=True))

@app.route("/callback")
def callback():
    token = google.authorize_access_token()
    user = token['userinfo']
    session['user'] = {
        'email': user['email'],
        'name': user['name'],
    }
    return redirect('/')

@app.route("/logout")
def logout():
    session.clear()
    return redirect('/login')

@app.route("/api/clips")
def get_clips():
    if not session.get('user'):
        return jsonify([])
    sb = get_supabase()
    response = sb.table("clips").select("*").execute()
    return jsonify(response.data)

@app.route("/api/sync", methods=["POST"])
def sync():
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
    app.run(debug=False)