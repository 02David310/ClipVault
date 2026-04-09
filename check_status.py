import os
import json
import datetime
from supabase import create_client
from dotenv import load_dotenv
import sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def check_status():
    BASE_DIR = get_base_dir()
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    
    print("=== ClipVault Status Check ===")
    
    search_email = input("\nBitte gib die E-Mail-Adresse ein: ").strip()
    
    # 1. Authentifizierungs-Check (Lokal)
    session_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ClipVault', 'session.json')
    if os.path.exists(session_path):
        ctime = os.path.getctime(session_path)
        dt_obj = datetime.datetime.fromtimestamp(ctime)
        print(f"[AUTH] Account lokal authentifiziert am: {dt_obj.strftime('%d.%m.%Y %H:%M:%S')}")
    else:
        print("[AUTH] Keine lokale token.json gefunden. Nutzer ist evtl. nicht eingeloggt.")

    # 2. Supabase Cloud Logs
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    
    if not url or not key:
        print("[ERROR] Supabase Zugangsdaten fehlen in der .env!")
        return

    try:
        supabase = create_client(url, key)
        
        # Letzten Clip abrufen
        response = supabase.table("clips") \
            .select("*") \
            .eq("user_id", search_email) \
            .order("uploaded_at", desc=True) \
            .limit(1) \
            .execute()

        if response.data:
            last_clip = response.data[0]
            print(f"[CLOUD] Letzter Clip Upload: {last_clip['uploaded_at']}")
            print(f"[CLOUD] Titel: {last_clip['title']} (Spiel: {last_clip['game']})")
            
            # Gesamtzahl der Clips
            count_res = supabase.table("clips").select("id", count="exact").eq("user_id", search_email).execute()
            print(f"[CLOUD] Gesamtanzahl Clips in der Vault: {count_res.count}")
        else:
            print(f"[CLOUD] Keine Clips für '{search_email}' in der Datenbank gefunden.")

    except Exception as e:
        print(f"[ERROR] Fehler beim Abrufen der Cloud-Daten: {e}")

    # 3. Letzte Zeilen der lokalen Log-Datei
    log_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ClipVault', 'watcher.log')
    if os.path.exists(log_path):
        print("\n--- Letzte 5 lokale Watcher-Logs ---")
        with open(log_path, "r") as f:
            lines = f.readlines()
            for line in lines[-5:]:
                print(line.strip())
    else:
        print("\n[LOG] Keine watcher.log Datei gefunden.")

    input("\nDrücke Enter zum Beenden...")

if __name__ == "__main__":
    check_status()