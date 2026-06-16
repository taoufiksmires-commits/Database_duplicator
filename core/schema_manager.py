import json
import os

SCHEMA_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "schema_cache.json")


class SchemaManager:
    def __init__(self, config, log_fn):
        self.config = config
        self._log = log_fn
        self._cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(SCHEMA_CACHE_PATH):
            with open(SCHEMA_CACHE_PATH, "r") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(SCHEMA_CACHE_PATH, "w") as f:
            json.dump(self._cache, f, indent=2)

    def check_and_migrate(self, src_conn, pair_id, src_table):
        current_sig = src_conn.get_schema_signature(src_table)
        cached_sig = self._cache.get(pair_id)

        if cached_sig is None:
            self._cache[pair_id] = current_sig
            self._save_cache()
            self._log("INFO", f"[{pair_id}] Schéma source enregistré.")
            return False

        if current_sig != cached_sig:
            self._log("WARN", f"[{pair_id}] Changement de schéma détecté !")
            new_table = self.config.increment_version(pair_id)
            self._cache[pair_id] = current_sig
            self._save_cache()
            self._log("INFO", f"[{pair_id}] Nouvelle table destination : {new_table}")
            return True

        return False

    def create_dest_table(self, src_conn, dst_conn, src_table, dest_table):
        create_sql = src_conn.get_create_table_sql(src_table)
        adapted_sql = create_sql.replace(
            f"CREATE TABLE `{src_table}`",
            f"CREATE TABLE IF NOT EXISTS `{dest_table}`"
        )
        dst_conn.execute_raw(adapted_sql)
        self._log("INFO", f"Table `{dest_table}` créée.")
