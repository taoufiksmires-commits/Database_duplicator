import uuid
from core.local_db import LocalDB, VERSION


class ConfigManager:
    def __init__(self, local_db: LocalDB):
        self._db = local_db

    @property
    def version(self):
        return VERSION

    @property
    def pairs(self):
        return self._db.get_pairs()

    @property
    def sync(self):
        s = self._db.get_all_settings()
        return {"interval_seconds": int(s.get("interval_seconds", 5))}

    @property
    def history(self):
        s = self._db.get_all_settings()
        return {
            "host":     s.get("history_host", "127.0.0.1"),
            "port":     int(s.get("history_port", 3306)),
            "user":     s.get("history_user", "root"),
            "password": s.get("history_password", ""),
            "database": s.get("history_database", "mysqlsync_history")
        }

    def get_pair(self, pair_id):
        for p in self.pairs:
            if p["id"] == pair_id:
                return p
        return None

    def add_pair(self, name="Nouvelle paire"):
        new_pair = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "enabled": True,
            "source": {
                "host": "", "port": 3306, "user": "root",
                "password": "", "database": "", "table": "", "primary_key": "id"
            },
            "destination": {
                "host": "", "port": 3306, "user": "root",
                "password": "", "database": "",
                "table_prefix": "sync_V", "current_version": 1
            }
        }
        self._db.save_pair(new_pair)
        return new_pair

    def update_pair(self, pair_id, updated):
        self._db.save_pair(updated)

    def remove_pair(self, pair_id):
        self._db.delete_pair(pair_id)

    def set_pair_enabled(self, pair_id, enabled):
        self._db.set_pair_enabled(pair_id, enabled)

    def get_dest_table_name(self, pair_id):
        pair = self.get_pair(pair_id)
        if pair:
            prefix = pair["destination"]["table_prefix"]
            version = pair["destination"]["current_version"]
            return f"{prefix}{version}"
        return None

    def increment_version(self, pair_id):
        pair = self.get_pair(pair_id)
        if pair:
            pair["destination"]["current_version"] += 1
            self._db.save_pair(pair)
            return self.get_dest_table_name(pair_id)
        return None

    def save_settings(self, settings_dict):
        for k, v in settings_dict.items():
            self._db.set_setting(k, v)

    def log_sync(self, pair_id, pair_name, src_table, dest_table, rows_added, rows_updated):
        self._db.log_sync(pair_id, pair_name, src_table, dest_table, rows_added, rows_updated)

    def fetch_history(self, limit=200):
        return self._db.fetch_history(limit)

    def get_from_id(self, pair_id):
        return self._db.get_pair_from_id(pair_id)

    def set_from_id(self, pair_id, from_id):
        self._db.set_pair_from_id(pair_id, from_id)
