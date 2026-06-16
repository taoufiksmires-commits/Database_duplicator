import threading
import time
import logging
from datetime import datetime
from core.db_connector import DBConnector
from core.schema_manager import SchemaManager

logger = logging.getLogger("SyncEngine")


class SyncEngine:
    def __init__(self, config):
        self.config = config
        self.running = False
        self._thread = None
        self._log_callbacks = []
        self.stats = {
            "total_rows_synced": 0,
            "total_errors": 0,
            "status": "Arrêté",
            "pairs": {}
        }

    def _init_pair_stats(self):
        for pair in self.config.pairs:
            pid = pair["id"]
            if pid not in self.stats["pairs"]:
                self.stats["pairs"][pid] = {
                    "name": pair["name"],
                    "rows_synced": 0,
                    "errors": 0,
                    "last_sync": None,
                    "dest_table": self.config.get_dest_table_name(pid),
                    "status": "En attente"
                }

    def add_log_callback(self, fn):
        self._log_callbacks.append(fn)

    def _log(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        full = f"[{ts}] [{level}] {msg}"
        for cb in self._log_callbacks:
            try:
                cb(level, full)
            except Exception:
                pass

    def start(self):
        if self.running:
            return
        self.running = True
        self.stats["status"] = "En cours"
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._log("INFO", "Moteur démarré.")

    def stop(self):
        self.running = False
        self.stats["status"] = "Arrêté"
        self._log("INFO", "Moteur arrêté.")

    def _loop(self):
        schema_mgr = SchemaManager(self.config, self._log)
        interval = self.config.sync.get("interval_seconds", 5)

        while self.running:
            self._init_pair_stats()
            for pair in self.config.pairs:
                if not pair.get("enabled", True):
                    continue
                try:
                    self._sync_pair(pair, schema_mgr)
                except Exception as e:
                    pid = pair["id"]
                    self.stats["pairs"].setdefault(pid, {})
                    self.stats["pairs"][pid]["errors"] = self.stats["pairs"][pid].get("errors", 0) + 1
                    self.stats["total_errors"] += 1
                    self.stats["pairs"][pid]["status"] = "Erreur"
                    self._log("ERROR", f"[{pair['name']}] {e}")
            time.sleep(interval)

    def _sync_pair(self, pair, schema_mgr):
        pid        = pair["id"]
        src_cfg    = pair["source"]
        pk         = src_cfg.get("primary_key", "id")
        src_table  = src_cfg["table"]
        dest_table = self.config.get_dest_table_name(pid)
        from_id    = self.config.get_from_id(pid)

        src = DBConnector(src_cfg)
        dst = DBConnector(pair["destination"])

        try:
            src.connect()
            dst.connect()

            changed = schema_mgr.check_and_migrate(src, pid, src_table)
            if changed:
                dest_table = self.config.get_dest_table_name(pid)
                self.stats["pairs"][pid]["dest_table"] = dest_table

            if not dst.table_exists(dest_table):
                schema_mgr.create_dest_table(src, dst, src_table, dest_table)

            src_rows = src.fetch_all_rows(src_table, pk=pk, from_id=from_id)
            if not src_rows:
                self.stats["pairs"][pid]["last_sync"] = datetime.now()
                self.stats["pairs"][pid]["status"] = "OK"
                return

            columns      = src.get_columns(src_table)
            dst_pks      = dst.fetch_all_pks(dest_table, pk)
            rows_added   = sum(1 for r in src_rows if r[pk] not in dst_pks)
            rows_updated = len(src_rows) - rows_added

            dst.upsert_rows(dest_table, columns, src_rows)

            if rows_added > 0:
                from_str = f" (depuis ID {from_id})" if from_id is not None else ""
                self._log("INFO", f"[{pair['name']}] +{rows_added} ajoutées → {dest_table}{from_str}")
                self.config.log_sync(pid, pair["name"], src_table, dest_table, rows_added, rows_updated)

            self.stats["pairs"][pid]["rows_synced"] = self.stats["pairs"][pid].get("rows_synced", 0) + rows_added
            self.stats["total_rows_synced"] += rows_added
            self.stats["pairs"][pid]["last_sync"] = datetime.now()
            self.stats["pairs"][pid]["status"] = "OK"

        finally:
            src.disconnect()
            dst.disconnect()
