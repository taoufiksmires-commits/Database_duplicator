import json
import os

DEFAULT_CONFIG = {
    "source": {
        "host": "192.168.1.10",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "source_db",
        "table": "source_table"
    },
    "destination": {
        "host": "192.168.1.20",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "dest_db",
        "table_prefix": "sync_data_V",
        "current_version": 1
    },
    "sync": {
        "interval_seconds": 5,
        "polling_column": "updated_at"
    }
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


class ConfigManager:
    def __init__(self):
        self._path = os.path.abspath(CONFIG_PATH)
        self._data = {}
        self.load()

    def load(self):
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                self._data = json.load(f)
        else:
            self._data = json.loads(json.dumps(DEFAULT_CONFIG))
            self.save()

    def save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, *keys):
        node = self._data
        for k in keys:
            node = node[k]
        return node

    def set(self, value, *keys):
        node = self._data
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value
        self.save()

    @property
    def source(self):
        return self._data["source"]

    @property
    def destination(self):
        return self._data["destination"]

    @property
    def sync(self):
        return self._data["sync"]

    def get_dest_table_name(self):
        prefix = self._data["destination"]["table_prefix"]
        version = self._data["destination"]["current_version"]
        return f"{prefix}{version}"

    def increment_version(self):
        self._data["destination"]["current_version"] += 1
        self.save()
        return self.get_dest_table_name()
