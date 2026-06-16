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
        self._lock = threading.Lock()
        self.stats = {
            "last_sync": None,
            "rows_synced": 0,
            "errors": 0,
            "status": "Arrêté",
            "current_dest_table": config.get_dest_table_name()
        }
        self._log_callbacks = []

    def add_log_callback(self, fn):
        self._log_callbacks.append(fn)

    def _log(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        full = f"[{ts}] [{level}] {msg}"
        logger.info(full)
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
        self._log("INFO", "Moteur de synchronisation démarré.")

    def stop(self):
        self.running = False
        self.stats["status"] = "Arrêté"
        self._log("INFO", "Moteur de synchronisation arrêté.")

    def _loop(self):
        schema_mgr = SchemaManager(self.config, self._log)
        interval = self.config.sync.get("interval_seconds", 5)

        while self.running:
            try:
                self._sync_once(schema_mgr)
            except Exception as e:
                self.stats["errors"] += 1
                self._log("ERROR", f"Erreur inattendue : {e}")
            time.sleep(interval)

    def _sync_once(self, schema_mgr):
        cfg_src = self.config.source
        cfg_dst = self.config.destination

        src = DBConnector(cfg_src)
        dst = DBConnector(cfg_dst)

        try:
            src.connect()
            dst.connect()

            src_table = cfg_src["table"]
            dest_table = self.config.get_dest_table_name()

            # Vérification / migration de schéma
            changed = schema_mgr.check_and_migrate(src, dst, src_table, dest_table)
            if changed:
                dest_table = self.config.get_dest_table_name()
                self.stats["current_dest_table"] = dest_table
                self._log("WARN", f"Nouveau schéma détecté → table destination : {dest_table}")

            # Création de la table destination si elle n'existe pas
            if not dst.table_exists(dest_table):
                schema_mgr.create_dest_table(src, dst, src_table, dest_table)
                self._log("INFO", f"Table {dest_table} créée.")

            # Récupération des nouvelles lignes / modifiées
            polling_col = self.config.sync.get("polling_column", "updated_at")
            last_sync = self.stats["last_sync"]

            if last_sync:
                rows = src.fetch_updated_rows(src_table, polling_col, last_sync)
            else:
                rows = src.fetch_all_rows(src_table)

            if rows:
                columns = src.get_columns(src_table)
                dst.upsert_rows(dest_table, columns, rows)
                self.stats["rows_synced"] += len(rows)
                self._log("INFO", f"{len(rows)} ligne(s) synchronisée(s) → {dest_table}")

            self.stats["last_sync"] = datetime.now()

        finally:
            src.disconnect()
            dst.disconnect()
