#!/usr/bin/env python3
import hmac
import queue
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request, send_from_directory, url_for

from config import ACCESS_CONFIG, APP_CONFIG, WIFI_CONFIG
from database import (
    create_user,
    get_firebase_queue_count,
    get_log_by_id,
    get_logs,
    get_user_by_nfc,
    get_user_fullname,
    is_user_checked_in,
    insert_log,
    test_database_connection,
)
from scanner import NFCStandbyReader
from firebase_adapter import firebase_status
from sync_service import retry_pending, sync_log_or_queue, sync_user_or_queue

app = Flask(__name__)
sync_queue = queue.Queue(maxsize=500)
tap_action_lock = threading.Lock()
processed_tap_counters = set()


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
    """Publish the card event first; the kiosk asks what the tap is for."""
    try:
        user = get_user_by_nfc(uid)
        checked_in = is_user_checked_in(uid) if user else False
    except Exception as exc:
        app.logger.warning("Unable to identify tapped card: %s", exc)
        user = None
        checked_in = False
    if not user:
        return {"message": "School ID detected"}
    return {
        "message": f"{user.get('fullname')} · ID detected",
        "payload": {
            "user": {
                "firstname": user.get("firstname"),
                "fullname": user.get("fullname"),
                "student_no": user.get("student_no"),
                "course": user.get("course"),
                "checked_in": checked_in,
            }
        },
    }


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


def render_airhub_page():
    page = (Path(app.root_path) / "index.html").read_text(encoding="utf-8")
    page = page.replace('data-runtime="preview"', 'data-runtime="pi"', 1)
    return Response(page, mimetype="text/html", headers={"Cache-Control": "no-store"})

@app.route("/")
def public_logs():
    return render_airhub_page()


@app.route("/login")
def login():
    return render_airhub_page()


@app.route("/styles.css")
def airhub_styles():
    return send_from_directory(app.root_path, "styles.css", max_age=0)


@app.route("/script.js")
def airhub_script():
    return send_from_directory(app.root_path, "script.js", max_age=0)


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


@app.route("/tap_action", methods=["POST"])
def tap_action():
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    uid = str(data.get("uid") or "").strip()
    try:
        tap_counter = int(data.get("tap_counter"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid tap session."}), 400

    if action not in {"check_in", "check_out", "appointment"} or not uid:
        return jsonify({"error": "Invalid tap action."}), 400

    latest = nfc_reader.latest_tap(-1)
    if not latest or latest.get("uid") != uid or latest.get("tap_counter") != tap_counter:
        return jsonify({"error": "This tap has expired. Please tap your ID again."}), 409

    with tap_action_lock:
        if tap_counter in processed_tap_counters:
            return jsonify({"error": "This tap has already been used."}), 409

        if action == "appointment":
            fullname = get_user_fullname(uid)
            if not fullname:
                return jsonify({"error": "This ID is not registered for appointments."}), 403
            return jsonify({"success": True, "message": "Choose an appointment service."})

        if action == "check_out" and not is_user_checked_in(uid):
            processed_tap_counters.add(tap_counter)
            nfc_reader.update_user_state(uid, False)
            return jsonify({"success": True, "message": "Already checked out.", "log": None})

        if action == "check_in" and is_user_checked_in(uid):
            processed_tap_counters.add(tap_counter)
            nfc_reader.update_user_state(uid, True)
            return jsonify({"success": True, "message": "Already checked in.", "log": None})

        log_record = insert_log(uid)
        if not log_record:
            return jsonify({"error": "Unable to save attendance."}), 500
        processed_tap_counters.add(tap_counter)
        nfc_reader.update_user_state(uid, log_record.get("status") == "TAP_IN")

        if len(processed_tap_counters) > 256:
            processed_tap_counters.remove(min(processed_tap_counters))

    enqueue_sync("log", log_record)
    fullname = log_record.get("fullname") or get_user_fullname(uid) or "Guest"
    if log_record.get("status") == "TAP_OUT":
        duration = log_record.get("duration_label") or "00:00:00"
        message = f"Check out: {fullname}. Stayed {duration}."
    else:
        message = f"Check in: {fullname}"
    return jsonify({"success": True, "message": message, "log": log_record})


@app.route("/get_nfc_code")
def get_nfc_code():
    return jsonify({"nfc_code": nfc_reader.status().get("last_uid")})


@app.route("/validate_registration_code", methods=["POST"])
def validate_registration_code():
    data = request.get_json(silent=True) or {}
    supplied = str(data.get("code") or "")
    expected = str(ACCESS_CONFIG.get("registration_code") or "")
    if not expected or not hmac.compare_digest(supplied, expected):
        return jsonify({"error": "Incorrect registration code."}), 403
    return jsonify({"success": True})


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
