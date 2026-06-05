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
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def insert_log(nfc_code):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_logs (nfc_code) VALUES (%s)", (nfc_code,))
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_user_fullname(nfc_code):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT fullname FROM users WHERE nfc_code=%s", (nfc_code,))
        row = cursor.fetchone()
        return row[0] if row else None
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
            SELECT nfc_code, date_logged, status, fullname
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
