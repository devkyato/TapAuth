#!/usr/bin/env python3
from flask import Flask, jsonify, render_template, request

from config import APP_CONFIG, WIFI_CONFIG
from database import (
    create_user,
    get_logs,
    get_user_fullname,
    insert_log,
    test_database_connection,
)
from scanner import NFCStandbyReader

app = Flask(__name__)


def handle_tap(uid):
    insert_log(uid)
    fullname = get_user_fullname(uid) or "Guest"
    return f"Hi, {fullname}!"


nfc_reader = NFCStandbyReader(on_tap=handle_tap)
nfc_reader.start()


@app.route("/")
def public_logs():
    return render_template("login.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/airhub-register")
def index():
    return render_template("index.html")


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
        create_user(
            student_no=request.form["student_no"],
            lastname=request.form["lastname"],
            firstname=request.form["firstname"],
            middlename=request.form.get("middlename", ""),
            course=request.form["course"],
            project_type=request.form["project_type"],
            room=request.form["room"],
            nfc_code=request.form["nfc_code"],
        )
        return jsonify({"success": True, "message": "Registration successful."})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/user_logs_info")
def user_logs_info():
    try:
        return jsonify(get_logs(limit=100))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
