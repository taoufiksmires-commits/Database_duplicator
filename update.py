"""
update.py — Mise à jour de MySQLSync
Lancer avec : python update.py
"""
import urllib.request
import os
import json

BASE_URL = "https://raw.githubusercontent.com/TON_COMPTE/mysqlsync/main/"

FILES = [
    "main.py",
    "core/config_manager.py",
    "core/db_connector.py",
    "core/schema_manager.py",
    "core/sync_engine.py",
    "ui/supervision_window.py",
    "requirements.txt",
]

def update():
    print("=== MySQLSync Updater ===\n")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    updated = 0

    for rel_path in FILES:
        url = BASE_URL + rel_path
        dest = os.path.join(base_dir, rel_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"  ✔ {rel_path}")
            updated += 1
        except Exception as e:
            print(f"  ✘ {rel_path} — {e}")

    print(f"\n{updated}/{len(FILES)} fichiers mis à jour.")
    print("Relancez python main.py pour appliquer.\n")
    input("Appuyez sur Entrée pour fermer...")

if __name__ == "__main__":
    update()
