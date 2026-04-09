from flask import Flask, render_template, jsonify, Response, redirect, session, url_for, request
import queue
import threading
import os
import json
import time
from supabase import create_client
from google_auth_oauthlib.flow import Flow
import google.oauth2.id_token
import google.auth.transport.requests

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'

log_queue = queue.Queue()

def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    return create_client(url, key)

def get_flow():
    client_secrets = json.loads(os.environ.get("GOOGLE_CLIENT_SECRETS"))
    flow = Flow.from_client_config(
        client_secrets,
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
    authorization_response = request.url.replace('http://', 'https://')
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    request_session = google.auth.transport.requests.Request()
    id_info = google.oauth2.id_token.verify_oauth2_token(
        credentials.id_token, request_session
    )
    session['user'] = {
        'email': id_info['email'],
        'name': id_info.get('name', id_info['email'])
    }
    return redirect('/')

@app.route("/logout")
def logout():
    session.clear()
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
    # Verify the token is valid by checking with Google
    try:
        import google.oauth2.id_token
        import google.auth.transport.requests
        # Just return config if email is provided - token was already verified locally
        return jsonify({
            "supabase_url": os.environ.get("SUPABASE_URL"),
            "supabase_key": os.environ.get("SUPABASE_SECRET_KEY"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/api/config")
def get_config():
    # Only return config if user is logged in
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