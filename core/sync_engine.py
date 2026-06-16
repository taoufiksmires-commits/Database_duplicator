import threading
import time
import hashlib
import json
import logging
from datetime import datetime
from core.db_connector import DBConnector
from core.schema_manager import SchemaManager
from core.history_manager import HistoryManager

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
        self._init_pair_stats()

    def _init_pair_stats(self):
        for pair in self.config.pairs:
            self.stats["pairs"][pair["id"]] = {
                "name": pair["name"],
                "rows_synced": 0,
                "errors": 0,
                "last_sync": None,
                "dest_table": self.config.get_dest_table_name(pair["id"]),
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
        history_mgr = HistoryManager(self.config, self._log)
        history_mgr.connect()
        interval = self.config.sync.get("interval_seconds", 5)

        while self.running:
            for pair in self.config.pairs:
                if not pair.get("enabled", True):
                    continue
                try:
                    self._sync_pair(pair, schema_mgr, history_mgr)
                except Exception as e:
                    pid = pair["id"]
                    self.stats["pairs"][pid]["errors"] += 1
                    self.stats["total_errors"] += 1
                    self.stats["pairs"][pid]["status"] = "Erreur"
                    self._log("ERROR", f"[{pair['name']}] {e}")
            time.sleep(interval)

        history_mgr.disconnect()

    def _sync_pair(self, pair, schema_mgr, history_mgr):
        pid      = pair["id"]
        src_cfg  = pair["source"]
        dst_cfg  = pair["destination"]
        pk       = src_cfg.get("primary_key", "id")
        src_table = src_cfg["table"]
        dest_table = self.config.get_dest_table_name(pid)

        src = DBConnector(src_cfg)
        dst = DBConnector(dst_cfg)

        try:
            src.connect()
            dst.connect()

            # Vérif schéma
            changed = schema_mgr.check_and_migrate(src, pid, src_table)
            if changed:
                dest_table = self.config.get_dest_table_name(pid)
                self.stats["pairs"][pid]["dest_table"] = dest_table

            # Créer table destination si besoin
            if not dst.table_exists(dest_table):
                schema_mgr.create_dest_table(src, dst, src_table, dest_table)

            # Récupérer toutes les lignes source
            src_rows = src.fetch_all_rows(src_table)
            if not src_rows:
                self.stats["pairs"][pid]["last_sync"] = datetime.now()
                self.stats["pairs"][pid]["status"] = "OK"
                return

            columns = src.get_columns(src_table)

            # Récupérer les PKs destination pour détecter nouveaux vs modifiés
            dst_pks = dst.fetch_all_pks(dest_table, pk)
            src_pks = {row[pk] for row in src_rows}

            rows_added   = 0
            rows_updated = 0

            for row in src_rows:
                row_pk = row[pk]
                # Comparer le hash de la ligne avec ce qui est en destination
                if row_pk not in dst_pks:
                    rows_added += 1
                else:
                    rows_updated += 1

            if src_rows:
                dst.upsert_rows(dest_table, columns, src_rows)

            total = rows_added + rows_updated
            if total > 0:
                self._log("INFO", f"[{pair['name']}] +{rows_added} ajoutées, ~{rows_updated} vérifiées → {dest_table}")
                history_mgr.log(pid, pair["name"], src_table, dest_table, rows_added, rows_updated)

            self.stats["pairs"][pid]["rows_synced"] += rows_added
            self.stats["total_rows_synced"] += rows_added
            self.stats["pairs"][pid]["last_sync"] = datetime.now()
            self.stats["pairs"][pid]["status"] = "OK"

        finally:
            src.disconnect()
            dst.disconnect()
