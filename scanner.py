import subprocess
import threading
import time

from nfc_utils import canonicalize_nfc_uid

try:
    from pynfc import Nfc, Timeout
except Exception as exc:
    Nfc = None

    class Timeout(Exception):
        pass

    NFC_IMPORT_ERROR = exc
else:
    NFC_IMPORT_ERROR = None


def find_acr122u_usb_port():
    try:
        lsusb_output = subprocess.check_output(["lsusb"]).decode("utf-8", errors="ignore")
        for line in lsusb_output.splitlines():
            if "ACR122U" in line:
                parts = line.split()
                return parts[1]
    except Exception as exc:
        print(f"[USB] lsusb error: {exc}")
    return None


class NFCStandbyReader:
    def __init__(self, on_tap, debounce_seconds=1.0, cooldown_seconds=2.0):
        self.on_tap = on_tap
        self.debounce_seconds = debounce_seconds
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._connected = False
        self._last_error = None
        self._device_string = None
        self._tap_counter = 0
        self._last_uid = None
        self._last_uid_time = 0.0
        self._last_tap_timestamp = None
        self._last_message = None
        self._last_log_id = None
        self._last_payload = None
        self._cooldown = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()
            print("[NFC] Thread started")

    def status(self):
        with self._lock:
            return {
                "connected": self._connected,
                "device": self._device_string,
                "last_uid": self._last_uid,
                "last_tap_timestamp": self._last_tap_timestamp,
                "last_message": self._last_message,
                "tap_counter": self._tap_counter,
                "last_error": self._last_error,
                "last_log_id": self._last_log_id,
                "last_payload": self._last_payload,
            }

    def latest_tap(self, since_counter):
        with self._lock:
            if self._tap_counter == since_counter:
                return None
            return {
                "tap_counter": self._tap_counter,
                "uid": self._last_uid,
                "tap_timestamp": self._last_tap_timestamp,
                "message": self._last_message,
                "log_id": self._last_log_id,
                **(self._last_payload or {}),
            }

    def wait_for_tap(self, since_counter, timeout=15):
        with self._cond:
            changed = self._cond.wait_for(
                lambda: self._tap_counter != since_counter or self._stop.is_set(),
                timeout=timeout,
            )
            if not changed or self._tap_counter == since_counter:
                return None
            return {
                "tap_counter": self._tap_counter,
                "uid": self._last_uid,
                "tap_timestamp": self._last_tap_timestamp,
                "message": self._last_message,
                "log_id": self._last_log_id,
                **(self._last_payload or {}),
            }

    def update_user_state(self, uid, checked_in):
        with self._lock:
            if self._last_uid != uid or not self._last_payload:
                return
            user = self._last_payload.get("user")
            if isinstance(user, dict):
                user["checked_in"] = bool(checked_in)

    def cache_registered_user(self, uid, user):
        """Replace a just-registered card's stale unknown-card cache."""
        with self._lock:
            if self._last_uid != uid:
                return False
            safe_user = {
                "firstname": user.get("firstname"),
                "fullname": user.get("fullname"),
                "student_no": user.get("student_no"),
                "course": user.get("course"),
                "checked_in": bool(user.get("checked_in", False)),
            }
            self._last_payload = {"user": safe_user}
            self._last_message = f"{safe_user.get('fullname') or 'Student'} · ID registered"
            self._cooldown.pop(uid, None)
            return True

    def _set_error(self, message):
        with self._lock:
            self._last_error = message

    def _set_connected(self, connected, device=None):
        with self._lock:
            self._connected = connected
            if device is not None:
                self._device_string = device

    def _publish_tap(self, uid, message, log_id=None, payload=None):
        with self._cond:
            self._last_uid = uid
            self._last_uid_time = time.time()
            self._last_tap_timestamp = time.time()
            self._last_message = message
            self._last_log_id = log_id
            self._last_payload = payload
            self._tap_counter += 1
            self._cond.notify_all()

    def _accept_tap(self, uid):
        uid = canonicalize_nfc_uid(uid)
        if not uid:
            self._set_error("NFC reader returned an empty UID")
            return
        now = time.time()
        with self._lock:
            if uid == self._last_uid and (now - self._last_uid_time) < self.debounce_seconds:
                return

        last_logged = self._cooldown.get(uid, 0.0)
        if (now - last_logged) < self.cooldown_seconds:
            self._publish_tap(
                uid,
                self._last_message or f"NFC captured: {uid}",
                payload=self._last_payload,
            )
            return

        log_id = None
        payload = None
        try:
            result = self.on_tap(uid)
            if isinstance(result, dict):
                message = result.get("message", "Tap recorded")
                log_id = result.get("log_id")
                payload = result.get("payload")
            else:
                message = result
            self._cooldown[uid] = now
        except Exception as exc:
            message = f"Log failed: {exc}"
            self._set_error(str(exc))

        self._publish_tap(uid, message, log_id, payload)

    def _run(self):
        if Nfc is None:
            self._set_error(f"pynfc is not installed/importable: {NFC_IMPORT_ERROR}")
            print(f"[NFC] pynfc import failed: {NFC_IMPORT_ERROR}")
            return

        backoff = 1.0
        while not self._stop.is_set():
            port = find_acr122u_usb_port()
            if not port:
                self._set_connected(False, device=None)
                self._set_error("ACR122U not found in lsusb")
                time.sleep(1)
                continue

            device_candidates = [f"acr122_usb:{port}", "acr122_usb"]
            self._set_connected(False, device=device_candidates[0])

            try:
                self._set_error(None)
                nfc = None
                last_open_error = None
                for device in device_candidates:
                    try:
                        nfc = Nfc(device)
                        break
                    except Exception as exc:
                        last_open_error = exc
                if nfc is None:
                    raise last_open_error or RuntimeError("Unable to open ACR122U")
                self._set_connected(True, device=device)
                backoff = 1.0

                for target in nfc.poll():
                    if self._stop.is_set():
                        break
                    try:
                        self._accept_tap(target.uid)
                    except Timeout:
                        pass
                    except Exception as exc:
                        self._set_error(f"Read/decode error: {exc}")
            except Exception as exc:
                self._set_connected(False, device=device)
                self._set_error(f"Open/poll failed: {exc}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 10.0)
