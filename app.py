from flask import Flask, render_template, jsonify, Response
import queue
import threading
import os
import json
import folder_uploader
import time

app = Flask(__name__)
log_queue = queue.Queue()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CLIPS_FILE = os.path.join(DATA_DIR, "clips.json")

def run_upload(folder):
    time.sleep(1)
    def callback(message):
        log_queue.put(message)
    folder_uploader.log_callback = callback
    folder_uploader.upload_folder(folder)
    log_queue.put("__DONE__")

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/api/clips")
def get_clips():
    if not os.path.exists(CLIPS_FILE):
        return jsonify([])
    with open(CLIPS_FILE, "r") as f:
        return jsonify(json.load(f))

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