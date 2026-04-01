from flask import Flask, render_template, jsonify, Response
import queue
import threading
import os
import json
import folder_uploader
import time
from supabase import create_client

app = Flask(__name__)
log_queue = queue.Queue()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/api/clips")
def get_clips():
    response = supabase.table("clips").select("*").execute()
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