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
        return {"signature": None}

    def _save_cache(self):
        with open(SCHEMA_CACHE_PATH, "w") as f:
            json.dump(self._cache, f, indent=2)

    def check_and_migrate(self, src_conn, dst_conn, src_table, dest_table):
        """
        Compare la signature du schéma source avec le cache.
        Si changement → incrémente la version et retourne True.
        """
        current_sig = src_conn.get_schema_signature(src_table)
        cached_sig = self._cache.get("signature")

        if cached_sig is None:
            # Premier démarrage : on enregistre le schéma actuel
            self._cache["signature"] = current_sig
            self._save_cache()
            self._log("INFO", "Schéma source enregistré pour la première fois.")
            return False

        if current_sig != cached_sig:
            self._log("WARN", "Changement de schéma détecté sur la table source !")
            new_table = self.config.increment_version()
            self._cache["signature"] = current_sig
            self._save_cache()
            self._log("INFO", f"Version incrémentée → nouvelle table destination : {new_table}")
            return True

        return False

    def create_dest_table(self, src_conn, dst_conn, src_table, dest_table):
        """
        Crée la table destination en copiant la structure source
        avec le nouveau nom.
        """
        create_sql = src_conn.get_create_table_sql(src_table)
        # Remplacer le nom de table source par le nom destination
        adapted_sql = create_sql.replace(
            f"CREATE TABLE `{src_table}`",
            f"CREATE TABLE IF NOT EXISTS `{dest_table}`"
        )
        dst_conn.execute_raw(adapted_sql)
        self._log("INFO", f"Table `{dest_table}` créée depuis la structure de `{src_table}`.")
