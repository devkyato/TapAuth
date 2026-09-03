try:
    import mysql.connector
except ImportError:
    mysql = None

from config import APP_CONFIG, MYSQL_CONFIG
from nfc_utils import canonicalize_nfc_uid


USER_COLUMNS = (
    "id",
    "student_no",
    "lastname",
    "firstname",
    "middlename",
    "fullname",
    "course",
    "project_type",
    "room",
    "nfc_code",
    "created_at",
)

RESERVATION_COLUMNS = (
    "id", "service", "nfc_code", "fullname", "student_no", "course",
    "reservation_date", "schedule_time", "duration_minutes", "queue_position",
    "teacher_name", "project_name", "purpose", "notes", "model_file_name",
    "model_file_path", "status", "created_at", "updated_at",
)


def get_connection():
    if mysql is None:
        raise RuntimeError("MySQL support is not installed. Use AIRHUB_STORAGE=sqlite or install requirements-mysql.txt.")
    return mysql.connector.connect(**MYSQL_CONFIG)


def test_database_connection():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return {
            "connected": True,
            "driver": "mysql",
            "database": MYSQL_CONFIG["database"],
            "admin": "phpMyAdmin",
        }
    except Exception as exc:
        return {
            "connected": False,
            "driver": "mysql",
            "database": MYSQL_CONFIG["database"],
            "admin": "phpMyAdmin",
            "error": str(exc),
        }
    finally:
        close(cursor, conn)


def close(cursor=None, conn=None):
    if cursor:
        cursor.close()
    if conn and conn.is_connected():
        conn.close()


def normalize(value):
    return (value or "").strip().upper()


def create_user(student_no, lastname, firstname, middlename, course, project_type, room, nfc_code):
    nfc_code = canonicalize_nfc_uid(nfc_code)
    if not nfc_code:
        raise ValueError("A valid NFC UID is required.")
    fullname = " ".join(
        part for part in (normalize(firstname), normalize(middlename), normalize(lastname)) if part
    )
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users
            (student_no, lastname, firstname, middlename, fullname, course, project_type, room, nfc_code)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                student_no=VALUES(student_no),
                lastname=VALUES(lastname),
                firstname=VALUES(firstname),
                middlename=VALUES(middlename),
                fullname=VALUES(fullname),
                course=VALUES(course),
                project_type=VALUES(project_type),
                room=VALUES(room)
            """,
            (
                student_no.strip(),
                normalize(lastname),
                normalize(firstname),
                normalize(middlename),
                fullname,
                normalize(course),
                normalize(project_type),
                normalize(room),
                nfc_code,
            ),
        )
        conn.commit()
        user = get_user_by_nfc(nfc_code)
        if not user:
            raise RuntimeError("The student record could not be read after registration.")
        return user
    finally:
        close(cursor, conn)


def insert_log(nfc_code):
    nfc_code = canonicalize_nfc_uid(nfc_code)
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_logs (nfc_code) VALUES (%s)", (nfc_code,))
        log_id = cursor.lastrowid
        conn.commit()
        return get_log_by_id(log_id)
    finally:
        close(cursor, conn)


def is_user_checked_in(nfc_code):
    nfc_code = canonicalize_nfc_uid(nfc_code)
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT COUNT(*) AS tap_count
            FROM user_logs
            WHERE nfc_code=%s AND DATE(date_logged)=CURDATE()
            """,
            (nfc_code,),
        )
        row = cursor.fetchone() or {}
        return int(row.get("tap_count") or 0) % 2 == 1
    finally:
        close(cursor, conn)


def get_user_fullname(nfc_code):
    user = get_user_by_nfc(nfc_code)
    return user["fullname"] if user else None


def get_user_by_nfc(nfc_code):
    nfc_code = canonicalize_nfc_uid(nfc_code)
    if not nfc_code:
        return None
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"""
            SELECT {", ".join(USER_COLUMNS)}
            FROM users
            WHERE nfc_code=%s
               OR REPLACE(
                    UPPER(
                      REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                          TRIM(nfc_code), ':', ''), '-', ''), ' ', ''), '.', ''), '_', '')
                    ),
                    '0X',
                    ''
                  )=%s
            ORDER BY (nfc_code=%s) DESC, id DESC
            LIMIT 1
            """,
            (nfc_code, nfc_code, nfc_code),
        )
        user = cursor.fetchone()
        if user and user.get("nfc_code") != nfc_code:
            old_nfc_code = user.get("nfc_code")
            try:
                cursor.execute("UPDATE users SET nfc_code=%s WHERE id=%s", (nfc_code, user["id"]))
                cursor.execute("UPDATE user_logs SET nfc_code=%s WHERE nfc_code=%s", (nfc_code, old_nfc_code))
                conn.commit()
                user["nfc_code"] = nfc_code
            except mysql.connector.IntegrityError:
                conn.rollback()
        return user
    finally:
        close(cursor, conn)


def get_user_by_id(user_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"""
            SELECT {", ".join(USER_COLUMNS)}
            FROM users
            WHERE id=%s
            """,
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        close(cursor, conn)


def get_log_by_id(log_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_logs_info WHERE id=%s", (log_id,))
        return cursor.fetchone()
    finally:
        close(cursor, conn)


def get_logs(limit=100):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT *
            FROM user_logs_info
            ORDER BY date_logged DESC, id DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()
    finally:
        close(cursor, conn)


def get_all_users():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"""
            SELECT {", ".join(USER_COLUMNS)}
            FROM users
            ORDER BY id ASC
            """
        )
        return cursor.fetchall()
    finally:
        close(cursor, conn)


def delete_user(user_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"SELECT {', '.join(USER_COLUMNS)} FROM users WHERE id=%s",
            (user_id,),
        )
        user = cursor.fetchone()
        if not user:
            return None
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        return user
    finally:
        close(cursor, conn)


def get_all_logs():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_logs_info ORDER BY date_logged ASC, id ASC")
        return cursor.fetchall()
    finally:
        close(cursor, conn)


def create_reservation(service, nfc_code, fullname, student_no, course, reservation_date,
                       schedule_time=None, duration_minutes=None, teacher_name=None,
                       project_name=None, purpose=None, notes=None, model_file_name=None,
                       model_file_path=None):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        queue_position = None
        if service == "printing":
            cursor.execute(
                "SELECT COALESCE(MAX(queue_position), 0) + 1 AS next_position "
                "FROM reservations WHERE service='printing' AND reservation_date=%s FOR UPDATE",
                (reservation_date,),
            )
            queue_position = int((cursor.fetchone() or {}).get("next_position") or 1)
        cursor.execute(
            """
            INSERT INTO reservations
            (service, nfc_code, fullname, student_no, course, reservation_date,
             schedule_time, duration_minutes, queue_position, teacher_name,
             project_name, purpose, notes, model_file_name, model_file_path)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (service, nfc_code, fullname, student_no, course, reservation_date,
             schedule_time, duration_minutes, queue_position, teacher_name,
             project_name, purpose, notes, model_file_name, model_file_path),
        )
        reservation_id = cursor.lastrowid
        conn.commit()
        return get_reservation_by_id(reservation_id)
    finally:
        close(cursor, conn)


def get_reservation_by_id(reservation_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"SELECT {', '.join(RESERVATION_COLUMNS)} FROM reservations WHERE id=%s",
            (reservation_id,),
        )
        return cursor.fetchone()
    finally:
        close(cursor, conn)


def get_reservations(limit=100):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"SELECT {', '.join(RESERVATION_COLUMNS)} FROM reservations "
            "ORDER BY reservation_date ASC, queue_position ASC, created_at ASC LIMIT %s",
            (limit,),
        )
        return cursor.fetchall()
    finally:
        close(cursor, conn)


def update_reservation_status(reservation_id, status):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE reservations SET status=%s WHERE id=%s", (status, reservation_id))
        conn.commit()
        return get_reservation_by_id(reservation_id) if cursor.rowcount else None
    finally:
        close(cursor, conn)


def enqueue_firebase_sync(record_type, record_id, error=None):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO firebase_sync_queue (record_type, record_id, attempts, last_error)
            VALUES (%s, %s, 0, %s)
            ON DUPLICATE KEY UPDATE
                synced_at=NULL,
                last_error=VALUES(last_error),
                updated_at=CURRENT_TIMESTAMP
            """,
            (record_type, record_id, error),
        )
        conn.commit()
    finally:
        close(cursor, conn)


def get_pending_firebase_sync(limit=100):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, record_type, record_id, attempts, last_error, created_at, updated_at
            FROM firebase_sync_queue
            WHERE synced_at IS NULL
            ORDER BY updated_at ASC, id ASC
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()
    finally:
        close(cursor, conn)


def mark_firebase_sync_done(queue_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE firebase_sync_queue
            SET synced_at=CURRENT_TIMESTAMP, last_error=NULL, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            (queue_id,),
        )
        conn.commit()
    finally:
        close(cursor, conn)


def mark_firebase_sync_failed(queue_id, error):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE firebase_sync_queue
            SET attempts=attempts+1, last_error=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            (str(error)[:1000], queue_id),
        )
        conn.commit()
    finally:
        close(cursor, conn)


def get_firebase_queue_count():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN synced_at IS NULL THEN 1 ELSE 0 END) AS pending,
                COUNT(*) AS total
            FROM firebase_sync_queue
            """
        )
        row = cursor.fetchone() or {}
        return {"pending": int(row.get("pending") or 0), "total": int(row.get("total") or 0)}
    finally:
        close(cursor, conn)


def enqueue_cloud_sync(target, record_type, record_id, error=None):
    return enqueue_firebase_sync(record_type, record_id, f"[{target}] {error or ''}".strip())


def get_pending_cloud_sync(limit=100):
    return [{**item, "target": "supabase"} for item in get_pending_firebase_sync(limit)]


def mark_cloud_sync_done(queue_id):
    return mark_firebase_sync_done(queue_id)


def mark_cloud_sync_failed(queue_id, error):
    return mark_firebase_sync_failed(queue_id, error)


def get_cloud_queue_count():
    return get_firebase_queue_count()


# SQLite is the default Raspberry Pi backend. The MySQL implementation above is
# retained for existing installations that explicitly set AIRHUB_STORAGE=mysql.
if APP_CONFIG.get("active_storage") == "sqlite":
    from sqlite_database import (
        create_reservation,
        create_user,
        delete_user,
        enqueue_cloud_sync,
        enqueue_firebase_sync,
        get_all_logs,
        get_all_users,
        get_cloud_queue_count,
        get_firebase_queue_count,
        get_log_by_id,
        get_pending_cloud_sync,
        get_pending_firebase_sync,
        get_reservation_by_id,
        get_reservations,
        get_user_by_id,
        get_user_by_nfc,
        get_user_fullname,
        get_logs,
        insert_log,
        is_user_checked_in,
        mark_cloud_sync_done,
        mark_cloud_sync_failed,
        mark_firebase_sync_done,
        mark_firebase_sync_failed,
        test_database_connection,
        update_reservation_status,
    )
