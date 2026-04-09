import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS = os.path.join(BASE_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

def get_youtube_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
    creds = flow.run_local_server(port=0)
    return build("youtube", "v3", credentials=creds)

def upload_video(video_path: str, title: str, description: str = "", privacy: str = "unlisted"):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    youtube = get_youtube_service()

    body = {
        "snippet": {
            "title": title,
            "description": description.strip(),  # no hashtags
            "categoryId": "20",  # Gaming (change if needed)
        },
        "status": {
            "privacyStatus": privacy,  # default = unlisted
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

    print(f"Uploading '{os.path.basename(video_path)}'...")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    print(f"\nDone! https://youtube.com/watch?v={response['id']}")

if __name__ == "__main__":
    video_path = input("Drag & drop video here: ").strip().strip("'\"")

    title = input("Title (Enter = filename): ").strip()
    if not title:
        title = os.path.splitext(os.path.basename(video_path))[0]

    description = input("Description (optional): ").strip()

    privacy = input("Privacy [unlisted/private/public] (Enter = unlisted): ").strip() or "unlisted"

    upload_video(video_path, title, description, privacy)