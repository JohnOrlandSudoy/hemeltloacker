"""SQLite persistence for registered users."""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import config
from hardware import camera as cam_hw

logger = logging.getLogger(__name__)


def _ensure_dirs() -> None:
    config.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    config.FACES_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def _connect():
    _ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                fingerprint_id INTEGER,
                rfid_uid TEXT,
                face_encoding BLOB,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                method TEXT,
                success INTEGER NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
    logger.info("Database ready at %s", config.DB_PATH)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def add_user(
    name: str,
    fingerprint_id: int | None,
    rfid_uid: str | None,
    face_encoding: list[float] | None,
) -> int:
    blob = cam_hw.encoding_to_bytes(face_encoding) if face_encoding else None
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (name, fingerprint_id, rfid_uid, face_encoding, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), fingerprint_id, rfid_uid, blob, now),
        )
        user_id = cur.lastrowid
    if face_encoding and user_id:
        cam_hw.save_face_photo(user_id, face_encoding)
    logger.info("User registered: %s (id=%s)", name, user_id)
    return user_id


def list_users() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, fingerprint_id, rfid_uid, created_at FROM users ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_dict(row)


def get_user_by_name(name: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE name = ?", (name.strip(),)).fetchone()
    return _row_to_dict(row)


def get_user_by_fingerprint(fp_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE fingerprint_id = ?", (fp_id,)
        ).fetchone()
    return _row_to_dict(row)


def get_user_by_rfid(rfid_uid: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE rfid_uid = ?", (rfid_uid,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT * FROM users WHERE rfid_uid = ?", (rfid_uid.upper(),)
            ).fetchone()
    return _row_to_dict(row)


def get_all_face_encodings() -> list[tuple[int, str, list[float]]]:
    result = []
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, face_encoding FROM users WHERE face_encoding IS NOT NULL"
        ).fetchall()
    for row in rows:
        enc = cam_hw.bytes_to_encoding(row["face_encoding"])
        result.append((row["id"], row["name"], enc))
    return result


def delete_user(user_id: int) -> bool:
    rowcount = 0
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        rowcount = cur.rowcount
    path = config.FACES_DIR / f"user_{user_id}.pkl"
    if path.exists():
        path.unlink()
    return rowcount > 0


def log_access(
    success: bool,
    method: str,
    message: str,
    user_id: int | None = None,
    user_name: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO access_log (user_id, user_name, method, success, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, user_name, method, 1 if success else 0, message, now),
        )
    line = f"{now} | {method} | {'OK' if success else 'DENY'} | {user_name or '-'} | {message}\n"
    try:
        with open(config.LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def get_recent_logs(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT user_name, method, success, message, created_at
            FROM access_log ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("DB initialized at", config.DB_PATH)
    print("Users:", list_users())
