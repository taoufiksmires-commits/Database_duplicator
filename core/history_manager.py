from datetime import datetime
from core.db_connector import DBConnector


class HistoryManager:
    def __init__(self, config, log_fn):
        self.config = config
        self._log = log_fn
        self._conn = None
        self._ready = False

    def connect(self):
        try:
            self._conn = DBConnector(self.config.history)
            self._conn.connect()
            self._ensure_table()
            self._ready = True
        except Exception as e:
            self._log("WARN", f"Historique indisponible : {e}")
            self._ready = False

    def disconnect(self):
        if self._conn:
            try:
                self._conn.disconnect()
            except Exception:
                pass

    def _ensure_table(self):
        self._conn.execute_raw("""
            CREATE TABLE IF NOT EXISTS `sync_history` (
                `id`          BIGINT AUTO_INCREMENT PRIMARY KEY,
                `pair_id`     VARCHAR(32),
                `pair_name`   VARCHAR(128),
                `src_table`   VARCHAR(128),
                `dest_table`  VARCHAR(128),
                `rows_added`  INT DEFAULT 0,
                `rows_updated`INT DEFAULT 0,
                `synced_at`   DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    def log(self, pair_id, pair_name, src_table, dest_table, rows_added, rows_updated):
        if not self._ready:
            return
        try:
            self._conn.cursor.execute(
                "INSERT INTO `sync_history` "
                "(pair_id, pair_name, src_table, dest_table, rows_added, rows_updated, synced_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (pair_id, pair_name, src_table, dest_table,
                 rows_added, rows_updated, datetime.now())
            )
            self._conn.conn.commit()
        except Exception as e:
            self._log("WARN", f"Erreur écriture historique : {e}")

    def fetch_recent(self, limit=100):
        if not self._ready:
            return []
        try:
            self._conn.cursor.execute(
                "SELECT * FROM `sync_history` ORDER BY synced_at DESC LIMIT %s",
                (limit,)
            )
            return self._conn.cursor.fetchall()
        except Exception:
            return []
