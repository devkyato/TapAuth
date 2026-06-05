import subprocess
import threading
import time

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
                bus = parts[1]
                device = parts[3].replace(":", "")
                return f"{bus}:{device}"
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
        self._last_message = None
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
                "last_message": self._last_message,
                "tap_counter": self._tap_counter,
                "last_error": self._last_error,
            }

    def latest_tap(self, since_counter):
        with self._lock:
            if self._tap_counter == since_counter:
                return None
            return {
                "tap_counter": self._tap_counter,
                "uid": self._last_uid,
                "message": self._last_message,
            }

    def _set_error(self, message):
        with self._lock:
            self._last_error = message

    def _set_connected(self, connected, device=None):
        with self._lock:
            self._connected = connected
            if device is not None:
                self._device_string = device

    def _publish_tap(self, uid, message):
        with self._cond:
            self._last_uid = uid
            self._last_uid_time = time.time()
            self._last_message = message
            self._tap_counter += 1
            self._cond.notify_all()

    def _accept_tap(self, uid):
        now = time.time()
        with self._lock:
            if uid == self._last_uid and (now - self._last_uid_time) < self.debounce_seconds:
                return

        last_logged = self._cooldown.get(uid, 0.0)
        if (now - last_logged) < self.cooldown_seconds:
            self._publish_tap(uid, self._last_message or f"NFC captured: {uid}")
            return

        try:
            message = self.on_tap(uid)
            self._cooldown[uid] = now
        except Exception as exc:
            message = f"Log failed: {exc}"
            self._set_error(str(exc))

        self._publish_tap(uid, message)

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

            device = f"acr122_usb:{port}"
            self._set_connected(False, device=device)

            try:
                self._set_error(None)
                nfc = Nfc(device)
                self._set_connected(True, device=device)
                backoff = 1.0

                for target in nfc.poll():
                    if self._stop.is_set():
                        break
                    try:
                        self._accept_tap(target.uid.decode())
                    except Timeout:
                        pass
                    except Exception as exc:
                        self._set_error(f"Read/decode error: {exc}")
            except Exception as exc:
                self._set_connected(False, device=device)
                self._set_error(f"Open/poll failed: {exc}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 10.0)
