"""Unlock logic — verify credentials and pulse solenoid."""
import logging
import time
from dataclasses import dataclass

import config
from database import db
from hardware import camera, fingerprint, rfid, solenoid

logger = logging.getLogger(__name__)

_last_unlock_time = 0.0


@dataclass
class UnlockResult:
    success: bool
    user_name: str | None
    method: str | None
    message: str


def _debounced() -> bool:
    global _last_unlock_time
    if time.time() - _last_unlock_time < config.UNLOCK_DEBOUNCE_SEC:
        return True
    return False


def _record_unlock(user: dict, method: str) -> UnlockResult:
    global _last_unlock_time
    name = user["name"]
    solenoid.unlock()
    _last_unlock_time = time.time()
    db.log_access(True, method, "Unlocked", user["id"], name)
    return UnlockResult(True, name, method, f"Welcome, {name}! Locker open.")


def _deny(method: str, msg: str) -> UnlockResult:
    db.log_access(False, method, msg)
    return UnlockResult(False, None, method, msg)


def try_unlock_from_fingerprint() -> UnlockResult:
    if _debounced():
        return UnlockResult(False, None, "fingerprint", "Please wait before trying again")
    pos = fingerprint.search(timeout_sec=15)
    if pos is None:
        return _deny("fingerprint", "Fingerprint not recognized")
    user = db.get_user_by_fingerprint(pos)
    if not user:
        return _deny("fingerprint", "Fingerprint not registered")
    return _record_unlock(user, "fingerprint")


def try_unlock_from_rfid() -> UnlockResult:
    if _debounced():
        return UnlockResult(False, None, "rfid", "Please wait before trying again")
    uid = rfid.read_uid(timeout_sec=10)
    if not uid:
        return UnlockResult(False, None, "rfid", "No card detected")
    user = db.get_user_by_rfid(uid)
    if not user:
        return _deny("rfid", "RFID card not registered")
    return _record_unlock(user, "rfid")


def try_unlock_from_face() -> UnlockResult:
    if _debounced():
        return UnlockResult(False, None, "face", "Please wait before trying again")
    encoding = camera.capture_encoding()
    if not encoding:
        return _deny("face", "No face detected")
    known = db.get_all_face_encodings()
    match = camera.find_matching_user(encoding, known)
    if not match:
        return _deny("face", "Face not recognized")
    user_id, name = match
    user = db.get_user_by_id(user_id)
    if not user:
        return _deny("face", "User record missing")
    return _record_unlock(user, "face")


def try_unlock_any(
    fp_id: int | None = None,
    rfid_uid: str | None = None,
    face_encoding: list | None = None,
) -> UnlockResult:
    """
    Programmatic unlock check (e.g. combined policy).
    Uses UNLOCK_POLICY from config.
    """
    if _debounced():
        return UnlockResult(False, None, None, "Please wait before trying again")

    matches = []

    if fp_id is not None:
        u = db.get_user_by_fingerprint(fp_id)
        if u:
            matches.append(("fingerprint", u))

    if rfid_uid is not None:
        u = db.get_user_by_rfid(rfid_uid)
        if u:
            matches.append(("rfid", u))

    if face_encoding is not None:
        known = db.get_all_face_encodings()
        m = camera.find_matching_user(face_encoding, known)
        if m:
            u = db.get_user_by_id(m[0])
            if u:
                matches.append(("face", u))

    policy = config.UNLOCK_POLICY
    if not matches:
        return UnlockResult(False, None, None, "Access denied")

    if policy == "any_one":
        return _record_unlock(matches[0][1], matches[0][0])

    if policy == "all_three":
        if len({m[1]["id"] for m in matches}) != 1 or len(matches) < 3:
            return UnlockResult(False, None, None, "All three methods required")
        return _record_unlock(matches[0][1], "all_three")

    if policy == "two_of_three":
        from collections import Counter

        ids = [m[1]["id"] for m in matches]
        uid, count = Counter(ids).most_common(1)[0]
        if count < 2:
            return UnlockResult(False, None, None, "Two methods required")
        user = next(m[1] for m in matches if m[1]["id"] == uid)
        return _record_unlock(user, "two_of_three")

    return _record_unlock(matches[0][1], matches[0][0])


def poll_unlock_once() -> UnlockResult | None:
    """
    Non-blocking style: try RFID quick read, else None.
    Used by background thread in UI.
    """
    uid = rfid.read_uid(timeout_sec=0.5)
    if uid:
        return try_unlock_any(rfid_uid=uid)
    return None
