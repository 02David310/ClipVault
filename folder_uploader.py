import json
from datetime import datetime
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import time
import sys

log_callback = None

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CLIPS_FILE = os.path.join(DATA_DIR, "clips.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
CLIENT_SECRETS = os.path.join(BASE_DIR, "client_secrets.json")

def get_client_secrets():
    env_secrets = os.environ.get("GOOGLE_CLIENT_SECRETS")
    if env_secrets:
        return json.loads(env_secrets)
    return None

def get_youtube_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            secrets = get_client_secrets()
            if secrets:
                flow = InstalledAppFlow.from_client_config(secrets, SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def log(message):
    print(message)
    if log_callback:
        log_callback(message)

def sync_clips():
    if not os.path.exists(CLIPS_FILE):
        return
    with open(CLIPS_FILE, "r") as f:
        clips = json.load(f)
    if not clips:
        return
    youtube = get_youtube_service()
    ids = [clip["video_id"] for clip in clips]
    response = youtube.videos().list(
        part="id,status",
        id=",".join(ids)
    ).execute()
    existing_ids = {
        item["id"] for item in response.get("items", [])
        if item["status"]["privacyStatus"] in ("unlisted", "public")
    }
    before = len(clips)
    clips = [c for c in clips if c["video_id"] in existing_ids]
    removed = before - len(clips)
    with open(CLIPS_FILE, "w") as f:
        json.dump(clips, f, indent=4)
    if removed:
        log(f"Sync: removed {removed} clips from clips.json")
    else:
        log("Sync: all clips are valid")

def get_or_create_playlist(youtube, game_name):
    response = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    for playlist in response.get("items", []):
        if playlist["snippet"]["title"].lower() == game_name.lower():
            log(f"Found existing playlist for '{game_name}'")
            return playlist["id"]
    log(f"Creating new playlist for '{game_name}'")
    res = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": game_name, "description": f"Clips - {game_name}"},
            "status": {"privacyStatus": "unlisted"},
        },
    ).execute()
    return res["id"]

def save_clip(title, game, video_id):
    user_id = os.environ.get("CLIPVAULT_USER_ID", "klopp.david310@gmail.com")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    
    if url and key:
        from supabase import create_client
        sb = create_client(url, key)
        sb.table("clips").insert({
            "title": title,
            "game": game,
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
            "uploaded_at": datetime.now().isoformat(),
            "user_id": user_id,
        }).execute()
    else:
        clips = []
        if os.path.exists(CLIPS_FILE):
            try:
                with open(CLIPS_FILE, "r") as f:
                    clips = json.load(f)
            except (json.JSONDecodeError, ValueError):
                clips = []
        clips.append({
            "title": title,
            "game": game,
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
            "uploaded_at": datetime.now().isoformat(),
            "user_id": user_id,
        })
        with open(CLIPS_FILE, "w") as f:
            json.dump(clips, f, indent=4)

def upload_single(file_path):
    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0]
    game_name = os.path.basename(os.path.dirname(file_path))
    log(f"Uploading '{filename}' from '{game_name}'")
    youtube = get_youtube_service()
    try:
        response = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": "",
                    "tags": ["upload", game_name],
                    "categoryId": "20",
                },
                "status": {"privacyStatus": "unlisted"},
            },
            media_body=MediaFileUpload(file_path, mimetype="video/mp4", resumable=True),
        ).execute()
        video_id = response['id']
        save_clip(title, game_name, video_id)
        log(f"https://youtube.com/watch?v={video_id}")
        playlist_id = get_or_create_playlist(youtube, game_name)
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()
        log(f"Added to '{game_name}' playlist!")
        os.remove(file_path)
        log(f"Deleted local file: {file_path}")
    except Exception as e:
        log(f"Failed: {e}")
    log("Done!")

def upload_folder(folder_path):
    videos = [f for f in os.listdir(folder_path) if f.lower().endswith((".mp4"))]
    if not videos:
        log("Folder is empty, nothing to upload")
        return
    log(f"Found {len(videos)} videos in '{folder_path}'")
    youtube = get_youtube_service()
    for i, filename in enumerate(videos, 1):
        video_path = os.path.join(folder_path, filename)
        title = os.path.splitext(filename)[0]
        log(f"[{i}/{len(videos)}] Uploading '{filename}'")
        try:
            response = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": "",
                        "tags": ["folder upload"],
                        "categoryId": "22",
                    },
                    "status": {"privacyStatus": "unlisted"},
                },
                media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
            ).execute()
            log(f"https://youtube.com/watch?v={response['id']}")
        except Exception as e:
            log(f"it didnt work'{filename}': {e}")
        if i < len(videos):
            time.sleep(10)
    log("Done!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("folder path: ").strip("\"")
    upload_folder(folder)