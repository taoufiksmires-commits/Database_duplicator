import json
import os
import uuid

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

DEFAULT_CONFIG = {
    "pairs": [
        {
            "id": str(uuid.uuid4())[:8],
            "name": "Paire 1",
            "enabled": True,
            "source": {
                "host": "192.168.1.10",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "source_db",
                "table": "source_table",
                "primary_key": "id"
            },
            "destination": {
                "host": "192.168.1.20",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "dest_db",
                "table_prefix": "sync_data_V",
                "current_version": 1
            }
        }
    ],
    "history": {
        "host": "192.168.1.20",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "mysqlsync_history"
    },
    "sync": {
        "interval_seconds": 5
    }
}


class ConfigManager:
    def __init__(self):
        self._path = os.path.abspath(CONFIG_PATH)
        self._data = {}
        self.load()

    def load(self):
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = json.loads(json.dumps(DEFAULT_CONFIG))
            self.save()

    def save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    @property
    def pairs(self):
        return self._data.get("pairs", [])

    @property
    def history(self):
        return self._data.get("history", {})

    @property
    def sync(self):
        return self._data.get("sync", {})

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
                "host": "",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "",
                "table": "",
                "primary_key": "id"
            },
            "destination": {
                "host": "",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "",
                "table_prefix": "sync_V",
                "current_version": 1
            }
        }
        self._data["pairs"].append(new_pair)
        self.save()
        return new_pair

    def remove_pair(self, pair_id):
        self._data["pairs"] = [p for p in self._data["pairs"] if p["id"] != pair_id]
        self.save()

    def update_pair(self, pair_id, updated):
        for i, p in enumerate(self._data["pairs"]):
            if p["id"] == pair_id:
                self._data["pairs"][i] = updated
                break
        self.save()

    def increment_version(self, pair_id):
        for p in self._data["pairs"]:
            if p["id"] == pair_id:
                p["destination"]["current_version"] += 1
                self.save()
                return self.get_dest_table_name(pair_id)
        return None

    def get_dest_table_name(self, pair_id):
        pair = self.get_pair(pair_id)
        if pair:
            prefix = pair["destination"]["table_prefix"]
            version = pair["destination"]["current_version"]
            return f"{prefix}{version}"
        return None

    def set_pair_enabled(self, pair_id, enabled):
        for p in self._data["pairs"]:
            if p["id"] == pair_id:
                p["enabled"] = enabled
                self.save()
                break
