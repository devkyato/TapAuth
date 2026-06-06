#!/usr/bin/env python3
import queue
import threading

from flask import Flask, jsonify, redirect, render_template, request, url_for

from config import ACCESS_CONFIG, APP_CONFIG, WIFI_CONFIG
from database import (
    create_user,
    get_firebase_queue_count,
    get_log_by_id,
    get_logs,
    get_user_fullname,
    insert_log,
    test_database_connection,
)
from scanner import NFCStandbyReader
from firebase_adapter import firebase_status
from sync_service import retry_pending, sync_log_or_queue, sync_user_or_queue

app = Flask(__name__)
sync_queue = queue.Queue(maxsize=500)


def enqueue_sync(record_type, record):
    try:
        sync_queue.put_nowait((record_type, record))
    except queue.Full:
        app.logger.warning("Firebase sync queue is full; record will remain in local MySQL only for now.")


def firebase_sync_worker():
    while True:
        record_type, record = sync_queue.get()
        try:
            if record_type == "user":
                sync_user_or_queue(record)
            else:
                sync_log_or_queue(record)
            retry_pending(limit=5)
        except Exception as exc:
            app.logger.warning("Background Firebase sync failed: %s", exc)
        finally:
            sync_queue.task_done()


threading.Thread(target=firebase_sync_worker, daemon=True).start()


def handle_tap(uid):
    log_record = insert_log(uid)
    enqueue_sync("log", log_record)
    fullname = log_record.get("fullname") if log_record else get_user_fullname(uid)
    if not fullname or (log_record and str(log_record.get("status", "")).startswith("GUEST")):
        return {"message": "Guest tap recorded.", "log_id": log_record.get("id")}
    if log_record.get("status") == "TAP_OUT":
        duration = log_record.get("duration_label") or "00:00:00"
        return {"message": f"Log out: {fullname}. Stayed {duration}.", "log_id": log_record.get("id")}
    return {"message": f"Login: {fullname}", "log_id": log_record.get("id")}


nfc_reader = NFCStandbyReader(on_tap=handle_tap)
nfc_reader.start()


def registration_authorized():
    code = ACCESS_CONFIG.get("registration_code", "")
    if not code:
        return True
    supplied = (
        request.args.get("code")
        or request.form.get("access_code")
        or request.headers.get("X-Airhub-Code")
    )
    return supplied == code

@app.route("/")
def public_logs():
    return render_template("login.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/airhub-register")
def index():
    if not registration_authorized():
        return "Registration is locked.", 403
    return render_template("index.html", access_code=request.args.get("code", ""))


@app.route("/registration")
def registration_link():
    return redirect(url_for("index", code=request.args.get("code", "")))


@app.route("/system_status")
def system_status():
    db_status = test_database_connection()
    return jsonify(
        {
            "app": APP_CONFIG,
            "wifi": {
                "ssid": WIFI_CONFIG["ssid"],
                "password_configured": bool(WIFI_CONFIG["password"]),
            },
            "database": db_status,
            "firebase": firebase_status(),
            "scanner": nfc_reader.status(),
        }
    )


@app.route("/nfc_status")
def nfc_status():
    return jsonify(nfc_reader.status())


@app.route("/latest_tap")
def latest_tap():
    try:
        since = int(request.args.get("since", 0))
    except (TypeError, ValueError):
        since = 0

    data = nfc_reader.latest_tap(since)
    if not data:
        return jsonify({"changed": False, "tap_counter": since})
    return jsonify({"changed": True, **data})


@app.route("/get_nfc_code")
def get_nfc_code():
    return jsonify({"nfc_code": nfc_reader.status().get("last_uid")})


@app.route("/register", methods=["POST"])
def register():
    if not registration_authorized():
        return jsonify({"error": "Registration is locked."}), 403

    required_fields = (
        "student_no",
        "lastname",
        "firstname",
        "course",
        "project_type",
        "room",
        "nfc_code",
    )
    missing = [field for field in required_fields if not request.form.get(field)]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400

    try:
        user_record = create_user(
            student_no=request.form["student_no"],
            lastname=request.form["lastname"],
            firstname=request.form["firstname"],
            middlename=request.form.get("middlename", ""),
            course=request.form["course"],
            project_type=request.form["project_type"],
            room=request.form["room"],
            nfc_code=request.form["nfc_code"],
        )
        enqueue_sync("user", user_record)
        return jsonify({"success": True, "message": "Registration successful."})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@app.route("/firebase_sync_status")
def firebase_sync_status():
    return jsonify({**get_firebase_queue_count(), "local_queue": sync_queue.qsize(), "firebase": firebase_status()})


@app.route("/retry_firebase_sync", methods=["POST"])
def retry_firebase_sync():
    return jsonify(retry_pending(limit=200))

@app.route("/user_logs_info")
def user_logs_info():
    try:
        return jsonify(get_logs(limit=8))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=APP_CONFIG.get("debug", False), use_reloader=False)
