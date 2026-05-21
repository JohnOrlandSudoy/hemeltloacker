"""User registration — fingerprint, RFID, and face."""
import logging
from dataclasses import dataclass

from database import db
from hardware import camera, fingerprint, rfid

logger = logging.getLogger(__name__)


@dataclass
class RegistrationResult:
    success: bool
    user_id: int | None
    message: str


def register(
    name: str,
    on_status=None,
) -> RegistrationResult:
    """
    Full enrollment: name → fingerprint → RFID → face → save.
    on_status(str) optional callback for UI updates.
    """
    def status(msg: str):
        logger.info(msg)
        if on_status:
            on_status(msg)

    name = name.strip()
    if not name:
        return RegistrationResult(False, None, "Name is required")

    if db.get_user_by_name(name):
        return RegistrationResult(False, None, f"User '{name}' already exists")

    try:
        status("Step 1/3: Scan fingerprint twice...")
        fp_pos = fingerprint.enroll()
        if fp_pos is None:
            return RegistrationResult(False, None, "Fingerprint enrollment failed")

        if db.get_user_by_fingerprint(fp_pos):
            fingerprint.delete_template(fp_pos)
            return RegistrationResult(
                False, None, "Fingerprint already registered to another user"
            )

        status("Step 2/3: Tap RFID card on reader...")
        uid = rfid.read_uid(timeout_sec=60)
        if not uid:
            fingerprint.delete_template(fp_pos)
            return RegistrationResult(False, None, "RFID read timeout")

        if db.get_user_by_rfid(uid):
            fingerprint.delete_template(fp_pos)
            return RegistrationResult(False, None, "RFID card already registered")

        status("Step 3/3: Look at camera — capturing face...")
        encoding = camera.capture_encoding_averaged()
        if not encoding:
            fingerprint.delete_template(fp_pos)
            return RegistrationResult(False, None, "No face detected — try again")

        user_id = db.add_user(
            name=name,
            fingerprint_id=fp_pos,
            rfid_uid=uid,
            face_encoding=encoding,
        )
        db.log_access(True, "register", f"Registered {name}", user_id, name)
        status(f"Registered {name} successfully!")
        return RegistrationResult(True, user_id, f"Welcome, {name}! Registration complete.")

    except Exception as e:
        logger.exception("Registration failed")
        return RegistrationResult(False, None, str(e))
