"""
local_db.py
Gère la base de configuration locale sur 127.0.0.1
Toute la config (paires, historique, settings) est stockée dans mysqlsync_config
"""
import mysql.connector
import json
import os

VERSION = "2.1.0"

LOCAL_CFG_FILE = os.path.join(os.path.dirname(__file__), "..", "local_conn.json")


class LocalDB:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self._local_cfg = self._load_local_cfg()

    def _load_local_cfg(self):
        if os.path.exists(LOCAL_CFG_FILE):
            with open(LOCAL_CFG_FILE, "r") as f:
                return json.load(f)
        return None

    def save_local_cfg(self, password):
        cfg = {
            "host": "127.0.0.1",
            "port": 3306,
            "user": "root",
            "password": password,
            "database": "mysqlsync_config"
        }
        with open(LOCAL_CFG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        self._local_cfg = cfg

    def is_configured(self):
        return self._local_cfg is not None

    def connect(self):
        cfg = self._local_cfg
        # Créer la base si besoin
        tmp = mysql.connector.connect(
            host=cfg["host"], port=cfg["port"],
            user=cfg["user"], password=cfg["password"],
            connection_timeout=5
        )
        tmp.cursor().execute(
            "CREATE DATABASE IF NOT EXISTS `mysqlsync_config` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        tmp.close()

        self.conn = mysql.connector.connect(
            host=cfg["host"], port=cfg["port"],
            user=cfg["user"], password=cfg["password"],
            database="mysqlsync_config",
            connection_timeout=5
        )
        self.cursor = self.conn.cursor(dictionary=True)
        self._ensure_tables()

    def _ensure_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS `pairs` (
                `id`          VARCHAR(32) PRIMARY KEY,
                `name`        VARCHAR(128),
                `enabled`     TINYINT DEFAULT 1,
                `source`      TEXT,
                `destination` TEXT,
                `created_at`  DATETIME DEFAULT CURRENT_TIMESTAMP,
                `updated_at`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS `settings` (
                `key`   VARCHAR(64) PRIMARY KEY,
                `value` TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS `sync_history` (
                `id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
                `pair_id`      VARCHAR(32),
                `pair_name`    VARCHAR(128),
                `src_table`    VARCHAR(128),
                `dest_table`   VARCHAR(128),
                `rows_added`   INT DEFAULT 0,
                `rows_updated` INT DEFAULT 0,
                `synced_at`    DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.conn.commit()

        # Valeurs par défaut settings
        defaults = {
            "interval_seconds": "5",
            "history_host": "127.0.0.1",
            "history_port": "3306",
            "history_user": "root",
            "history_password": "",
            "history_database": "mysqlsync_history",
            "version": VERSION
        }
        for k, v in defaults.items():
            self.cursor.execute(
                "INSERT IGNORE INTO `settings` (`key`, `value`) VALUES (%s, %s)", (k, v)
            )
        self.conn.commit()

    # ── Paires ────────────────────────────────────────────────────────────────
    def get_pairs(self):
        self.cursor.execute("SELECT * FROM `pairs` ORDER BY created_at")
        rows = self.cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id":          r["id"],
                "name":        r["name"],
                "enabled":     bool(r["enabled"]),
                "source":      json.loads(r["source"]),
                "destination": json.loads(r["destination"])
            })
        return result

    def save_pair(self, pair):
        self.cursor.execute(
            "INSERT INTO `pairs` (id, name, enabled, source, destination) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE name=%s, enabled=%s, source=%s, destination=%s",
            (
                pair["id"], pair["name"], int(pair.get("enabled", True)),
                json.dumps(pair["source"]), json.dumps(pair["destination"]),
                pair["name"], int(pair.get("enabled", True)),
                json.dumps(pair["source"]), json.dumps(pair["destination"])
            )
        )
        self.conn.commit()

    def delete_pair(self, pair_id):
        self.cursor.execute("DELETE FROM `pairs` WHERE id=%s", (pair_id,))
        self.conn.commit()

    def set_pair_enabled(self, pair_id, enabled):
        self.cursor.execute("UPDATE `pairs` SET enabled=%s WHERE id=%s", (int(enabled), pair_id))
        self.conn.commit()

    # ── Settings ──────────────────────────────────────────────────────────────
    def get_setting(self, key, default=None):
        self.cursor.execute("SELECT value FROM `settings` WHERE `key`=%s", (key,))
        row = self.cursor.fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.cursor.execute(
            "INSERT INTO `settings` (`key`, `value`) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE `value`=%s",
            (key, str(value), str(value))
        )
        self.conn.commit()

    def get_all_settings(self):
        self.cursor.execute("SELECT * FROM `settings`")
        return {r["key"]: r["value"] for r in self.cursor.fetchall()}

    # ── Historique ────────────────────────────────────────────────────────────
    def log_sync(self, pair_id, pair_name, src_table, dest_table, rows_added, rows_updated):
        self.cursor.execute(
            "INSERT INTO `sync_history` "
            "(pair_id, pair_name, src_table, dest_table, rows_added, rows_updated) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (pair_id, pair_name, src_table, dest_table, rows_added, rows_updated)
        )
        self.conn.commit()

    def fetch_history(self, limit=200):
        self.cursor.execute(
            "SELECT * FROM `sync_history` ORDER BY synced_at DESC LIMIT %s", (limit,)
        )
        return self.cursor.fetchall()

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_pair_from_id(self, pair_id):
        """Retourne le from_id configuré pour cette paire (None = depuis le début)."""
        self.cursor.execute(
            "SELECT value FROM `settings` WHERE `key`=%s",
            (f"from_id_{pair_id}",)
        )
        row = self.cursor.fetchone()
        if row and row["value"] not in (None, "", "None"):
            try:
                return int(row["value"])
            except ValueError:
                return None
        return None

    def set_pair_from_id(self, pair_id, from_id):
        """Enregistre le from_id pour une paire (None = depuis le début)."""
        val = str(from_id) if from_id is not None else ""
        self.cursor.execute(
            "INSERT INTO `settings` (`key`, `value`) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE `value`=%s",
            (f"from_id_{pair_id}", val, val)
        )
        self.conn.commit()
