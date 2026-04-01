import sqlite3
import json
from typing import Dict, List, Optional, Any


class LocalDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    usuario TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    activo INTEGER DEFAULT 1,
                    updated_at TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS forms (
                    form_id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    sheet_destino TEXT NOT NULL,
                    activo INTEGER DEFAULT 1,
                    updated_at TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS form_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    form_id TEXT NOT NULL,
                    campo TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    calculo TEXT,
                    opciones TEXT,
                    orden INTEGER DEFAULT 0,
                    obligatorio INTEGER DEFAULT 0,
                    editable INTEGER DEFAULT 1,
                    UNIQUE(form_id, campo)
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    local_id TEXT PRIMARY KEY,
                    form_id TEXT NOT NULL,
                    usuario TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    synced_at TEXT,
                    delete_after TEXT,
                    remote_id TEXT,
                    error_msg TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_records_status ON records(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_records_delete_after ON records(delete_after)")

    # Users
    def upsert_users(self, users: List[Dict[str, Any]]):
        with self._conn() as conn:
            c = conn.cursor()
            for u in users:
                c.execute(
                    """
                    INSERT INTO users (id, usuario, password, activo, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      usuario=excluded.usuario,
                      password=excluded.password,
                      activo=excluded.activo,
                      updated_at=excluded.updated_at
                    """,
                    (
                        str(u.get("id")),
                        u.get("usuario", ""),
                        u.get("password", ""),
                        1 if u.get("activo", True) else 0,
                        u.get("updated_at"),
                    ),
                )

    def validate_login(self, username: str, password: str) -> bool:
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT 1 FROM users WHERE usuario=? AND password=? AND activo=1 LIMIT 1",
                (username, password),
            )
            return c.fetchone() is not None

    def ensure_local_user(self, username: str, password: str):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO users (id, usuario, password, activo, updated_at)
                VALUES (?, ?, ?, 1, datetime('now'))
                ON CONFLICT(usuario) DO UPDATE SET
                  password=excluded.password,
                  activo=1,
                  updated_at=excluded.updated_at
                """,
                (f"local_{username}", username, password),
            )

    def ensure_local_users(self, users: List[Dict[str, Any]]):
        for u in users:
            username = str(u.get("usuario", "")).strip()
            password = str(u.get("password", "")).strip()
            if not username or not password:
                continue
            self.ensure_local_user(username, password)

    # Forms/Catalog
    def replace_forms_catalog(self, forms: List[Dict[str, Any]], fields: List[Dict[str, Any]]):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM forms")
            c.execute("DELETE FROM form_fields")

            for f in forms:
                c.execute(
                    """
                    INSERT INTO forms (form_id, nombre, sheet_destino, activo, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        f["form_id"],
                        f["nombre"],
                        f.get("sheet_destino", f["nombre"]),
                        1 if f.get("activo", True) else 0,
                        f.get("updated_at"),
                    ),
                )

            for fld in fields:
                c.execute(
                    """
                    INSERT INTO form_fields (form_id, campo, tipo, calculo, opciones, orden, obligatorio, editable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fld["form_id"],
                        fld["campo"],
                        fld["tipo"],
                        fld.get("calculo"),
                        json.dumps(fld.get("opciones", []), ensure_ascii=False),
                        int(fld.get("orden", 0)),
                        1 if fld.get("obligatorio", False) else 0,
                        1 if fld.get("editable", True) else 0,
                    ),
                )

    def get_forms(self):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM forms WHERE activo=1 ORDER BY nombre")
            return [dict(r) for r in c.fetchall()]

    def get_form_fields(self, form_id: str):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM form_fields WHERE form_id=? ORDER BY orden, id",
                (form_id,),
            )
            rows = []
            for r in c.fetchall():
                d = dict(r)
                d["opciones"] = json.loads(d["opciones"] or "[]")
                rows.append(d)
            return rows

    # Records
    def insert_record(self, local_id: str, form_id: str, usuario: str, payload: Dict[str, Any], created_at: str):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO records (local_id, form_id, usuario, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (local_id, form_id, usuario, json.dumps(payload, ensure_ascii=False), created_at),
            )

    def get_records_by_status(self, status: str, limit: int = 100):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM records WHERE status=? ORDER BY created_at LIMIT ?",
                (status, limit),
            )
            return [dict(r) for r in c.fetchall()]

    def get_pending_records(self, limit: int = 100):
        return self.get_records_by_status("pending", limit)

    def mark_synced(self, local_id: str, synced_at: str, delete_after: str, remote_id: Optional[str] = None):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                UPDATE records
                   SET status='synced', synced_at=?, delete_after=?, remote_id=?, error_msg=NULL
                 WHERE local_id=?
                """,
                (synced_at, delete_after, remote_id, local_id),
            )

    def mark_error(self, local_id: str, error_msg: str):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE records SET status='pending', error_msg=? WHERE local_id=?",
                (error_msg[:500], local_id),
            )

    def purge_synced_expired(self, now_iso: str) -> int:
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM records WHERE status='synced' AND delete_after IS NOT NULL AND delete_after<=?",
                (now_iso,),
            )
            return c.rowcount

    def get_records_dashboard(self):
        with self._conn() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) AS c FROM records WHERE status='pending'")
            pending = c.fetchone()["c"]

            c.execute("SELECT COUNT(*) AS c FROM records WHERE status='synced'")
            synced = c.fetchone()["c"]

            c.execute(
                "SELECT COUNT(*) AS c FROM records WHERE status='synced' AND delete_after<=datetime('now')"
            )
            ready_delete = c.fetchone()["c"]

            c.execute(
                "SELECT * FROM records ORDER BY COALESCE(synced_at, created_at) DESC LIMIT 200"
            )
            rows = [dict(r) for r in c.fetchall()]

            return {
                "pending": pending,
                "synced": synced,
                "ready_delete": ready_delete,
                "rows": rows,
            }
