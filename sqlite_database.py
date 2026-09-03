import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from config import SQLITE_CONFIG
from nfc_utils import canonicalize_nfc_uid


DB_PATH = Path(SQLITE_CONFIG["path"]).expanduser().resolve()
_schema_lock = threading.Lock()
_schema_ready = False


class ClosingConnection(sqlite3.Connection):
    """Commit or roll back like sqlite3.Connection, then always close."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

USER_COLUMNS = (
    "id", "student_no", "lastname", "firstname", "middlename", "fullname",
    "course", "project_type", "room", "nfc_code", "created_at",
)
RESERVATION_COLUMNS = (
    "id", "service", "nfc_code", "fullname", "student_no", "course",
    "reservation_date", "schedule_time", "duration_minutes", "queue_position",
    "teacher_name", "project_name", "purpose", "notes", "model_file_name",
    "model_file_path", "status", "created_at", "updated_at",
)


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no TEXT NOT NULL,
    lastname TEXT NOT NULL,
    firstname TEXT NOT NULL,
    middlename TEXT NOT NULL DEFAULT '',
    fullname TEXT NOT NULL,
    course TEXT NOT NULL,
    project_type TEXT NOT NULL,
    room TEXT NOT NULL,
    nfc_code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_users_student_no ON users(student_no);
CREATE INDEX IF NOT EXISTS idx_users_nfc_code ON users(nfc_code);
CREATE TABLE IF NOT EXISTS user_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nfc_code TEXT NOT NULL,
    date_logged TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_user_logs_card_time ON user_logs(nfc_code, date_logged);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT NOT NULL CHECK(service IN ('printing','teacher')),
    nfc_code TEXT NOT NULL,
    fullname TEXT NOT NULL,
    student_no TEXT NOT NULL,
    course TEXT NOT NULL,
    reservation_date TEXT NOT NULL,
    schedule_time TEXT,
    duration_minutes INTEGER,
    queue_position INTEGER,
    teacher_name TEXT,
    project_name TEXT,
    purpose TEXT,
    notes TEXT,
    model_file_name TEXT,
    model_file_path TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(service, reservation_date, queue_position)
);
CREATE INDEX IF NOT EXISTS idx_reservations_date ON reservations(reservation_date);
CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);
CREATE TABLE IF NOT EXISTS firebase_sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    synced_at TEXT,
    UNIQUE(record_type, record_id)
);
"""


def _connect():
    global _schema_ready
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    if not _schema_ready:
        with _schema_lock:
            if not _schema_ready:
                conn.executescript(SCHEMA)
                _schema_ready = True
    return conn


def _row(row):
    return dict(row) if row else None


def _normalize(value):
    return (value or "").strip().upper()


def test_database_connection():
    try:
        with _connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"connected": True, "driver": "sqlite", "database": str(DB_PATH), "admin": "TapAuth admin"}
    except Exception as exc:
        return {"connected": False, "driver": "sqlite", "database": str(DB_PATH), "admin": "TapAuth admin", "error": str(exc)}


def create_user(student_no, lastname, firstname, middlename, course, project_type, room, nfc_code):
    uid = canonicalize_nfc_uid(nfc_code)
    if not uid:
        raise ValueError("A valid NFC UID is required.")
    first, middle, last = _normalize(firstname), _normalize(middlename), _normalize(lastname)
    fullname = " ".join(part for part in (first, middle, last) if part)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO users(student_no, lastname, firstname, middlename, fullname, course, project_type, room, nfc_code)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(nfc_code) DO UPDATE SET
              student_no=excluded.student_no, lastname=excluded.lastname,
              firstname=excluded.firstname, middlename=excluded.middlename,
              fullname=excluded.fullname, course=excluded.course,
              project_type=excluded.project_type, room=excluded.room
        """, (student_no.strip(), last, first, middle, fullname, _normalize(course),
              _normalize(project_type), _normalize(room), uid))
    return get_user_by_nfc(uid)


def get_user_by_nfc(nfc_code):
    uid = canonicalize_nfc_uid(nfc_code)
    if not uid:
        return None
    with _connect() as conn:
        rows = conn.execute(f"SELECT {', '.join(USER_COLUMNS)} FROM users ORDER BY id DESC").fetchall()
        for row in rows:
            if canonicalize_nfc_uid(row["nfc_code"]) == uid:
                user = dict(row)
                if user["nfc_code"] != uid:
                    try:
                        conn.execute("UPDATE users SET nfc_code=? WHERE id=?", (uid, user["id"]))
                        conn.execute("UPDATE user_logs SET nfc_code=? WHERE nfc_code=?", (uid, user["nfc_code"]))
                        user["nfc_code"] = uid
                    except sqlite3.IntegrityError:
                        pass
                return user
    return None


def get_user_by_id(user_id):
    with _connect() as conn:
        return _row(conn.execute(f"SELECT {', '.join(USER_COLUMNS)} FROM users WHERE id=?", (user_id,)).fetchone())


def get_user_fullname(nfc_code):
    user = get_user_by_nfc(nfc_code)
    return user["fullname"] if user else None


def get_all_users():
    with _connect() as conn:
        return [dict(row) for row in conn.execute(f"SELECT {', '.join(USER_COLUMNS)} FROM users ORDER BY id").fetchall()]


def delete_user(user_id):
    with _connect() as conn:
        user = _row(conn.execute(f"SELECT {', '.join(USER_COLUMNS)} FROM users WHERE id=?", (user_id,)).fetchone())
        if user:
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        return user


def insert_log(nfc_code):
    uid = canonicalize_nfc_uid(nfc_code)
    with _connect() as conn:
        cursor = conn.execute("INSERT INTO user_logs(nfc_code) VALUES(?)", (uid,))
        log_id = cursor.lastrowid
    return get_log_by_id(log_id)


def is_user_checked_in(nfc_code):
    uid = canonicalize_nfc_uid(nfc_code)
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM user_logs WHERE nfc_code=? AND date(date_logged)=date('now','localtime')", (uid,)).fetchone()[0]
    return count % 2 == 1


def _all_enriched_logs():
    with _connect() as conn:
        rows = conn.execute("""
            SELECT l.id, l.nfc_code, l.date_logged, u.student_no, u.lastname,
                   u.firstname, u.fullname
            FROM user_logs l LEFT JOIN users u ON u.nfc_code=l.nfc_code
            ORDER BY l.date_logged, l.id
        """).fetchall()
    counters, previous, result = {}, {}, []
    for raw in rows:
        row = dict(raw)
        key = (row["nfc_code"], row["date_logged"][:10])
        counters[key] = counters.get(key, 0) + 1
        tap_in = counters[key] % 2 == 1
        entered = row["date_logged"] if tap_in else previous.get(key)
        duration = None
        if not tap_in and entered:
            duration = max(0, int((datetime.fromisoformat(row["date_logged"]) - datetime.fromisoformat(entered)).total_seconds()))
        row.update({
            "student_no": row.get("student_no") or "",
            "lastname": row.get("lastname") or "GUEST",
            "firstname": row.get("firstname") or "",
            "fullname": row.get("fullname") or "Guest",
            "status": "TAP_IN" if tap_in else "TAP_OUT",
            "event_type": "LOGIN" if tap_in else "LOGOUT",
            "time_entered": entered,
            "time_left": None if tap_in else row["date_logged"],
            "duration_seconds": duration,
            "duration_label": None if duration is None else f"{duration // 3600:02d}:{(duration % 3600) // 60:02d}:{duration % 60:02d}",
        })
        if tap_in:
            previous[key] = row["date_logged"]
        result.append(row)
    return result


def get_log_by_id(log_id):
    return next((row for row in _all_enriched_logs() if row["id"] == int(log_id)), None)


def get_logs(limit=100):
    return list(reversed(_all_enriched_logs()))[:int(limit)]


def get_all_logs():
    return _all_enriched_logs()


def create_reservation(service, nfc_code, fullname, student_no, course, reservation_date,
                       schedule_time=None, duration_minutes=None, teacher_name=None,
                       project_name=None, purpose=None, notes=None, model_file_name=None,
                       model_file_path=None):
    with _connect() as conn:
        queue_position = None
        if service == "printing":
            row = conn.execute("SELECT COALESCE(MAX(queue_position),0)+1 FROM reservations WHERE service='printing' AND reservation_date=?", (reservation_date,)).fetchone()
            queue_position = int(row[0])
        cursor = conn.execute("""
            INSERT INTO reservations(service,nfc_code,fullname,student_no,course,reservation_date,
              schedule_time,duration_minutes,queue_position,teacher_name,project_name,purpose,notes,
              model_file_name,model_file_path) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (service, canonicalize_nfc_uid(nfc_code), fullname, student_no, course, reservation_date,
              schedule_time, duration_minutes, queue_position, teacher_name, project_name, purpose,
              notes, model_file_name, model_file_path))
        reservation_id = cursor.lastrowid
    return get_reservation_by_id(reservation_id)


def get_reservation_by_id(reservation_id):
    with _connect() as conn:
        return _row(conn.execute(f"SELECT {', '.join(RESERVATION_COLUMNS)} FROM reservations WHERE id=?", (reservation_id,)).fetchone())


def get_reservations(limit=100):
    with _connect() as conn:
        rows = conn.execute(f"SELECT {', '.join(RESERVATION_COLUMNS)} FROM reservations ORDER BY reservation_date, queue_position, created_at LIMIT ?", (int(limit),)).fetchall()
        return [dict(row) for row in rows]


def update_reservation_status(reservation_id, status):
    with _connect() as conn:
        cursor = conn.execute("UPDATE reservations SET status=?, updated_at=datetime('now','localtime') WHERE id=?", (status, reservation_id))
    return get_reservation_by_id(reservation_id) if cursor.rowcount else None


def enqueue_firebase_sync(record_type, record_id, error=None):
    with _connect() as conn:
        conn.execute("""
            INSERT INTO firebase_sync_queue(record_type,record_id,last_error) VALUES(?,?,?)
            ON CONFLICT(record_type,record_id) DO UPDATE SET synced_at=NULL,
              last_error=excluded.last_error, updated_at=datetime('now','localtime')
        """, (record_type, record_id, error))


def get_pending_firebase_sync(limit=100):
    with _connect() as conn:
        rows = conn.execute("SELECT id,record_type,record_id,attempts,last_error,created_at,updated_at FROM firebase_sync_queue WHERE synced_at IS NULL ORDER BY updated_at,id LIMIT ?", (int(limit),)).fetchall()
        return [dict(row) for row in rows]


def mark_firebase_sync_done(queue_id):
    with _connect() as conn:
        conn.execute("UPDATE firebase_sync_queue SET synced_at=datetime('now','localtime'),last_error=NULL,updated_at=datetime('now','localtime') WHERE id=?", (queue_id,))


def mark_firebase_sync_failed(queue_id, error):
    with _connect() as conn:
        conn.execute("UPDATE firebase_sync_queue SET attempts=attempts+1,last_error=?,updated_at=datetime('now','localtime') WHERE id=?", (str(error)[:1000], queue_id))


def get_firebase_queue_count():
    with _connect() as conn:
        row = conn.execute("SELECT SUM(CASE WHEN synced_at IS NULL THEN 1 ELSE 0 END),COUNT(*) FROM firebase_sync_queue").fetchone()
    return {"pending": int(row[0] or 0), "total": int(row[1] or 0)}
