#!/usr/bin/env python3
import hmac
import queue
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from config import ACCESS_CONFIG, APP_CONFIG, FIREBASE_CONFIG, WIFI_CONFIG
from database import (
    create_user,
    create_reservation,
    delete_user,
    get_all_users,
    get_firebase_queue_count,
    get_log_by_id,
    get_logs,
    get_reservations,
    get_user_by_nfc,
    get_user_fullname,
    is_user_checked_in,
    insert_log,
    test_database_connection,
    update_reservation_status,
)
from scanner import NFCStandbyReader
from firebase_adapter import delete_user_from_firebase, firebase_status
from sync_service import retry_pending, sync_log_or_queue, sync_reservation_or_queue, sync_user_or_queue

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
sync_queue = queue.Queue(maxsize=500)
tap_action_lock = threading.Lock()
processed_tap_counters = set()
TAP_SESSION_MAX_AGE_SECONDS = 120
ALLOWED_MODEL_EXTENSIONS = {"stl", "obj", "3mf"}
MODEL_UPLOAD_DIR = Path(app.root_path) / "uploads" / "models"


@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify({"error": "The model file must be 100 MB or smaller."}), 413


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
            elif record_type == "reservation":
                sync_reservation_or_queue(record)
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
    code = ACCESS_CONFIG.get("admin_code", "")
    if not code:
        return False
    supplied = (
        request.args.get("code")
        or request.form.get("access_code")
        or request.headers.get("X-Airhub-Code")
    )
    return supplied == code


def admin_authorized():
    return registration_authorized()


def valid_latest_tap(uid, tap_counter):
    latest = nfc_reader.latest_tap(-1)
    if not latest or latest.get("uid") != uid or latest.get("tap_counter") != tap_counter:
        return None
    tapped_at = latest.get("tap_timestamp")
    if not tapped_at or time.time() - float(tapped_at) > TAP_SESSION_MAX_AGE_SECONDS:
        return None
    return latest


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


@app.route("/admin")
def admin_dashboard():
    if not admin_authorized():
        return render_template("admin_login.html"), 401
    return render_template(
        "admin.html",
        access_code=request.args.get("code", ""),
        firebase_project_id=FIREBASE_CONFIG.get("project_id", ""),
    )


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

    latest = valid_latest_tap(uid, tap_counter)
    if not latest:
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
    expected = str(ACCESS_CONFIG.get("admin_code") or "")
    if not expected or not hmac.compare_digest(supplied, expected):
        return jsonify({"error": "Incorrect registration code."}), 403
    return jsonify({"success": True})


@app.route("/register_from_tap", methods=["POST"])
def register_from_tap():
    """Register an unknown card only while its current NFC tap session is valid."""
    data = request.get_json(silent=True) or {}
    uid = str(data.get("uid") or "").strip()
    try:
        tap_counter = int(data.get("tap_counter"))
    except (TypeError, ValueError):
        return jsonify({"error": "Tap your card again to register."}), 400

    latest = valid_latest_tap(uid, tap_counter)
    if not latest:
        return jsonify({"error": "This tap has expired. Tap your card again."}), 409

    required = ("student_no", "firstname", "lastname", "course")
    missing = [field for field in required if not str(data.get(field) or "").strip()]
    if missing:
        return jsonify({"error": "Complete all required student details."}), 400

    try:
        existing_user = get_user_by_nfc(uid)
        if existing_user:
            nfc_reader.cache_registered_user(uid, {
                **existing_user,
                "checked_in": is_user_checked_in(uid),
            })
            return jsonify({
                "success": True,
                "message": "This card is already registered.",
                "user": {
                    "firstname": existing_user.get("firstname"),
                    "fullname": existing_user.get("fullname"),
                    "student_no": existing_user.get("student_no"),
                    "course": existing_user.get("course"),
                    "checked_in": is_user_checked_in(uid),
                },
            })

        user_record = create_user(
            student_no=str(data["student_no"]),
            lastname=str(data["lastname"]),
            firstname=str(data["firstname"]),
            middlename=str(data.get("middlename") or ""),
            course=str(data["course"]),
            project_type="STUDENT",
            room="AIRHUB",
            nfc_code=uid,
        )
        user_response = {
            "firstname": user_record.get("firstname"),
            "fullname": user_record.get("fullname"),
            "student_no": user_record.get("student_no"),
            "course": user_record.get("course"),
            "checked_in": False,
        }
        nfc_reader.cache_registered_user(uid, user_response)
        enqueue_sync("user", user_record)
        return jsonify({
            "success": True,
            "message": "Registration complete.",
            "user": user_response,
        })
    except Exception as exc:
        app.logger.exception("Tap registration failed")
        return jsonify({"error": "Unable to register this card. Check the local database."}), 500


@app.route("/admin/users")
def admin_users():
    if not admin_authorized():
        return jsonify({"error": "Admin access required."}), 403
    users = get_all_users()
    for user in users:
        user.pop("nfc_code", None)
    return jsonify(users)


@app.route("/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    if not admin_authorized():
        return jsonify({"error": "Admin access required."}), 403
    user = delete_user(user_id)
    if not user:
        return jsonify({"error": "Student not found."}), 404
    firebase_result = delete_user_from_firebase(user_id)
    return jsonify({
        "success": True,
        "message": f"{user.get('fullname')} was removed.",
        "firebase": firebase_result,
    })


@app.route("/reservations", methods=["POST"])
def create_reservation_request():
    uid = str(request.form.get("uid") or "").strip()
    try:
        tap_counter = int(request.form.get("tap_counter"))
    except (TypeError, ValueError):
        return jsonify({"error": "Tap your card again before making a reservation."}), 400
    if not valid_latest_tap(uid, tap_counter):
        return jsonify({"error": "This reservation session expired. Tap your card again."}), 409
    user = get_user_by_nfc(uid)
    if not user:
        return jsonify({"error": "Register this card before making a reservation."}), 403

    service = str(request.form.get("service") or "").strip().lower()
    reservation_date = str(request.form.get("date") or "").strip()
    if service not in {"printing", "teacher"} or not reservation_date:
        return jsonify({"error": "Complete the reservation details."}), 400

    model_path = None
    model_name = None
    try:
        if service == "printing":
            project_name = str(request.form.get("projectName") or "").strip()
            duration = str(request.form.get("duration") or "").strip()
            model = request.files.get("modelFile")
            if not project_name or not duration or not model or not model.filename:
                return jsonify({"error": "Date, duration, project name, and model file are required."}), 400
            try:
                duration_minutes = int(duration)
            except (TypeError, ValueError):
                return jsonify({"error": "The selected printing duration is invalid."}), 400
            safe_name = secure_filename(model.filename)
            extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
            if extension not in ALLOWED_MODEL_EXTENSIONS:
                return jsonify({"error": "Upload an STL, OBJ, or 3MF model file."}), 400
            MODEL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            stored_name = f"{uuid.uuid4().hex}.{extension}"
            model_path = MODEL_UPLOAD_DIR / stored_name
            model.save(model_path)
            model_name = safe_name
            record = create_reservation(
                service=service, nfc_code=uid, fullname=user["fullname"],
                student_no=user["student_no"], course=user["course"],
                reservation_date=reservation_date, duration_minutes=duration_minutes,
                project_name=project_name, notes=request.form.get("notes"),
                model_file_name=model_name,
                model_file_path=str(model_path.relative_to(app.root_path)),
            )
        else:
            teacher = str(request.form.get("teacher") or "").strip()
            schedule_time = str(request.form.get("time") or "").strip()
            purpose = str(request.form.get("purpose") or "").strip()
            if not teacher or not schedule_time or not purpose:
                return jsonify({"error": "Teacher, date, time, and purpose are required."}), 400
            record = create_reservation(
                service=service, nfc_code=uid, fullname=user["fullname"],
                student_no=user["student_no"], course=user["course"],
                reservation_date=reservation_date, schedule_time=schedule_time,
                teacher_name=teacher, purpose=purpose, notes=request.form.get("notes"),
            )
    except Exception:
        if model_path and model_path.exists():
            model_path.unlink()
        app.logger.exception("Unable to save reservation")
        return jsonify({"error": "Unable to save the reservation. Check the local database."}), 500

    enqueue_sync("reservation", record)
    return jsonify({
        "success": True,
        "reservation": {
            "id": record.get("id"), "service": record.get("service"),
            "date": str(record.get("reservation_date")),
            "time": str(record.get("schedule_time") or ""),
            "queuePosition": record.get("queue_position"),
            "status": record.get("status"),
        },
    })


@app.route("/reservations/current")
def current_reservations():
    rows = get_reservations(limit=50)
    return jsonify([{
        "id": row.get("id"), "service": row.get("service"),
        "date": str(row.get("reservation_date")),
        "time": str(row.get("schedule_time") or ""),
        "queuePosition": row.get("queue_position"), "status": row.get("status"),
    } for row in rows if row.get("status") in {"PENDING", "APPROVED"}])


@app.route("/admin/reservations")
def admin_reservations():
    if not admin_authorized():
        return jsonify({"error": "Admin access required."}), 403
    rows = get_reservations(limit=250)
    for row in rows:
        row.pop("nfc_code", None)
        row.pop("model_file_path", None)
        for field in ("reservation_date", "schedule_time", "created_at", "updated_at"):
            if row.get(field) is not None:
                row[field] = str(row[field])
    return jsonify(rows)


@app.route("/admin/reservations/<int:reservation_id>", methods=["PATCH"])
def admin_update_reservation(reservation_id):
    if not admin_authorized():
        return jsonify({"error": "Admin access required."}), 403
    status = str((request.get_json(silent=True) or {}).get("status") or "").upper()
    if status not in {"PENDING", "APPROVED", "DECLINED", "COMPLETED", "CANCELLED"}:
        return jsonify({"error": "Invalid reservation status."}), 400
    record = update_reservation_status(reservation_id, status)
    if not record:
        return jsonify({"error": "Reservation not found."}), 404
    enqueue_sync("reservation", record)
    return jsonify({"success": True, "message": "Reservation status updated."})


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
        return jsonify(get_logs(limit=25))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=APP_CONFIG.get("debug", False), use_reloader=False)
