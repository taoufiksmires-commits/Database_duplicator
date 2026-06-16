import mysql.connector


class DBConnector:
    def __init__(self, cfg):
        self.cfg = cfg
        self.conn = None
        self.cursor = None

    def connect(self):
        db_name = self.cfg["database"]
        tmp = mysql.connector.connect(
            host=self.cfg["host"],
            port=self.cfg.get("port", 3306),
            user=self.cfg["user"],
            password=self.cfg["password"],
            connection_timeout=5
        )
        tmp_cursor = tmp.cursor()
        tmp_cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        tmp_cursor.close()
        tmp.close()

        self.conn = mysql.connector.connect(
            host=self.cfg["host"],
            port=self.cfg.get("port", 3306),
            user=self.cfg["user"],
            password=self.cfg["password"],
            database=db_name,
            connection_timeout=5
        )
        self.cursor = self.conn.cursor(dictionary=True)

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def table_exists(self, table_name):
        self.cursor.execute(
            "SELECT COUNT(*) as c FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (self.cfg["database"], table_name)
        )
        return self.cursor.fetchone()["c"] > 0

    def get_columns(self, table_name):
        self.cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ORDINAL_POSITION",
            (self.cfg["database"], table_name)
        )
        return [r["COLUMN_NAME"] for r in self.cursor.fetchall()]

    def get_schema_signature(self, table_name):
        self.cursor.execute(
            "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ORDINAL_POSITION",
            (self.cfg["database"], table_name)
        )
        rows = self.cursor.fetchall()
        return "|".join(f"{r['COLUMN_NAME']}:{r['COLUMN_TYPE']}" for r in rows)

    def get_create_table_sql(self, table_name):
        self.cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
        row = self.cursor.fetchone()
        return row["Create Table"]

    def fetch_all_rows(self, table_name):
        self.cursor.execute(f"SELECT * FROM `{table_name}`")
        return self.cursor.fetchall()

    def fetch_rows_by_ids(self, table_name, pk, ids):
        fmt = ",".join(["%s"] * len(ids))
        self.cursor.execute(f"SELECT * FROM `{table_name}` WHERE `{pk}` IN ({fmt})", ids)
        return self.cursor.fetchall()

    def fetch_all_pks(self, table_name, pk):
        self.cursor.execute(f"SELECT `{pk}` FROM `{table_name}`")
        return {r[pk] for r in self.cursor.fetchall()}

    def upsert_rows(self, table_name, columns, rows):
        cols_escaped = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        updates = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in columns)
        sql = (
            f"INSERT INTO `{table_name}` ({cols_escaped}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {updates}"
        )
        for row in rows:
            values = [row.get(c) for c in columns]
            self.cursor.execute(sql, values)
        self.conn.commit()

    def execute_raw(self, sql):
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                self.cursor.execute(stmt)
        self.conn.commit()
