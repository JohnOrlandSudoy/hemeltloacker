"""AS608 fingerprint sensor over UART."""
import logging
import time

import config

logger = logging.getLogger(__name__)

_sensor = None


def _get_sensor():
    global _sensor
    if _sensor is not None:
        return _sensor
    if config.SIMULATE_HARDWARE:
        return None
    from pyfingerprint.pyfingerprint import PyFingerprint

    f = PyFingerprint(
        config.FINGERPRINT_PORT,
        config.FINGERPRINT_BAUD,
        config.FINGERPRINT_ADDRESS,
        config.FINGERPRINT_PASSWORD,
    )
    if not f.verifyPassword():
        raise ValueError("AS608 password verification failed")
    _sensor = f
    logger.info(
        "Fingerprint sensor ready. Templates: %s/%s",
        f.getTemplateCount(),
        f.getStorageCapacity(),
    )
    return _sensor


def get_template_count() -> int:
    if config.SIMULATE_HARDWARE:
        return 0
    return _get_sensor().getTemplateCount()


def enroll(position: int | None = None) -> int:
    """
    Enroll fingerprint at sensor position.
    Returns template position index.
    """
    if config.SIMULATE_HARDWARE:
        import random

        pos = position if position is not None else random.randint(1, 127)
        logger.info("Fingerprint enroll (simulated) position %s", pos)
        time.sleep(1)
        return pos

    f = _get_sensor()
    if position is None:
        position = f.getTemplateCount() + 1

    print("Place finger on sensor (1st scan)...")
    while f.readImage() != f.FINGERPRINT_OK:
        time.sleep(0.2)
    f.convertImage(0x01)
    while f.readImage() != f.FINGERPRINT_OK:
        time.sleep(0.2)
    print("Remove finger...")
    time.sleep(2)
    print("Place same finger again (2nd scan)...")
    while f.readImage() != f.FINGERPRINT_OK:
        time.sleep(0.2)
    f.convertImage(0x02)
    if f.createTemplate() != f.FINGERPRINT_OK:
        raise RuntimeError("Fingerprints did not match — try again")
    if f.storeTemplate(position, 0x01) != f.FINGERPRINT_OK:
        raise RuntimeError("Failed to store template")
    logger.info("Fingerprint stored at position %s", position)
    return position


def search(timeout_sec: float = 30.0) -> int | None:
    """
    Wait for finger scan and search sensor memory.
    Returns template position or None.
    """
    if config.SIMULATE_HARDWARE:
        import os

        sim = os.environ.get("HELMET_LOCKER_SIM_FP", "")
        if sim.isdigit():
            time.sleep(0.5)
            return int(sim)
        time.sleep(1)
        return None

    f = _get_sensor()
    deadline = time.time() + timeout_sec
    print("Place finger on sensor...")
    while time.time() < deadline:
        if f.readImage() == f.FINGERPRINT_OK:
            f.convertImage(0x01)
            try:
                result = f.searchTemplate()
                position = result[0]
                accuracy = result[1]
                logger.info("Match position %s accuracy %s", position, accuracy)
                return position
            except Exception:
                logger.debug("No fingerprint match")
                return None
        time.sleep(0.2)
    return None


def delete_template(position: int) -> bool:
    if config.SIMULATE_HARDWARE:
        return True
    f = _get_sensor()
    return f.deleteTemplate(position) == f.FINGERPRINT_OK


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Fingerprint test ===")
    print("1) Enroll  2) Search")
    choice = input("Choice [1/2]: ").strip()
    if choice == "1":
        pos = enroll()
        print("Enrolled at position:", pos)
    else:
        pos = search()
        print("Result:", pos if pos is not None else "No match")
