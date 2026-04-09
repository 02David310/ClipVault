import os
import sys
import subprocess
import ctypes
import shutil
import winreg

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Admin-Rechte anfordern
if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

print("=== ClipVault Uninstaller ===\n")

INSTALL_DIR = os.path.join(os.environ['LOCALAPPDATA'], "ClipVault")

# 1. Prozesse beenden
print("Beende ClipVault Prozesse...")
subprocess.run(["taskkill", "/F", "/IM", "ClipVault.exe", "/T"], capture_output=True, shell=True)
subprocess.run(["taskkill", "/F", "/IM", "ClipVaultWatcher.exe", "/T"], capture_output=True, shell=True)

# 2. Task Scheduler Eintrag entfernen
print("Entferne Autostart-Eintrag...")
subprocess.run(["schtasks", "/delete", "/tn", "ClipVault", "/f"], capture_output=True, shell=True)

# 3. Registry aufräumen (falls alte Einträge existieren)
try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    winreg.DeleteValue(key, "ClipVault")
    winreg.CloseKey(key)
    print("Registry-Einträge entfernt.")
except FileNotFoundError:
    pass

# 4. Ordner löschen
print(f"Lösche Dateien in {INSTALL_DIR}...")
if os.path.exists(INSTALL_DIR):
    try:
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
        print("✓ Dateien erfolgreich entfernt.")
    except Exception as e:
        print(f"Hinweis: Ordner konnte nicht sofort gelöscht werden: {e}")

print("\n✓ ClipVault wurde erfolgreich deinstalliert.")
input("\nDrücke Enter zum Beenden...")