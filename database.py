import mysql.connector

from config import MYSQL_CONFIG


def get_connection():
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
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def normalize(value):
    return (value or "").strip().upper()


def create_user(student_no, lastname, firstname, middlename, course, project_type, room, nfc_code):
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
                nfc_code.strip(),
            ),
        )
        conn.commit()
        return get_user_by_nfc(nfc_code)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_next_tap_type(cursor, nfc_code):
    cursor.execute(
        """
        SELECT tap_type
        FROM user_logs
        WHERE nfc_code=%s
          AND date_logged >= CURDATE()
          AND date_logged < CURDATE() + INTERVAL 1 DAY
        ORDER BY date_logged DESC, id DESC
        LIMIT 1
        """,
        (nfc_code,),
    )
    row = cursor.fetchone()
    last_tap_type = row[0] if row else None
    return "TAP_OUT" if last_tap_type == "TAP_IN" else "TAP_IN"


def insert_log(nfc_code, guest_name=None):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        tap_type = get_next_tap_type(cursor, nfc_code)
        cursor.execute(
            "INSERT INTO user_logs (nfc_code, guest_name, tap_type) VALUES (%s, %s, %s)",
            (nfc_code, guest_name, tap_type),
        )
        log_id = cursor.lastrowid
        conn.commit()
        return get_log_by_id(log_id)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_user_fullname(nfc_code):
    user = get_user_by_nfc(nfc_code)
    return user["fullname"] if user else None


def get_user_by_nfc(nfc_code):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, student_no, lastname, firstname, middlename, fullname, course, project_type, room, nfc_code, created_at, updated_at
            FROM users
            WHERE nfc_code=%s
            """,
            (nfc_code,),
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()




def get_user_by_id(user_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, student_no, lastname, firstname, middlename, fullname, course, project_type, room, nfc_code, created_at, updated_at
            FROM users
            WHERE id=%s
            """,
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def update_log_guest_name(log_id, guest_name):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE user_logs
            SET guest_name=%s
            WHERE id=%s
            """,
            ((guest_name or "").strip(), log_id),
        )
        conn.commit()
        return get_log_by_id(log_id)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_log_by_id(log_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, nfc_code, date_logged, status, fullname
            FROM user_logs_info
            WHERE id=%s
            """,
            (log_id,),
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_logs(limit=100):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, date_logged, status, fullname
            FROM user_logs_info
            ORDER BY date_logged DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_all_users():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, student_no, lastname, firstname, middlename, fullname, course, project_type, room, nfc_code, created_at, updated_at
            FROM users
            ORDER BY id ASC
            """
        )
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_all_logs():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, nfc_code, date_logged, status, fullname
            FROM user_logs_info
            ORDER BY date_logged ASC
            """
        )
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

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
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


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
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


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
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


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
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


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
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
