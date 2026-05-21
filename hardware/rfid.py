"""RC522 RFID reader over SPI."""
import logging
import time

import config

logger = logging.getLogger(__name__)

_reader = None


def _uid_to_hex(uid: list[int] | tuple) -> str:
    return ":".join(f"{b:02X}" for b in uid)


def _init_reader():
    global _reader
    if _reader is not None:
        return _reader
    if config.SIMULATE_HARDWARE:
        return None
    import RPi.GPIO as GPIO
    from mfrc522 import MFRC522

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(config.PIN_RFID_RST, GPIO.OUT)
    GPIO.output(config.PIN_RFID_RST, 1)
    _reader = MFRC522()
    return _reader


def read_uid(timeout_sec: float = 30.0, poll_interval: float = 0.2) -> str | None:
    """
    Block until a tag is presented or timeout.
    Returns UID string like '04:A1:B2:C3' or None.
    """
    if config.SIMULATE_HARDWARE:
        logger.info("RFID: simulation — use HELMET_LOCKER_SIM_UID env or default")
        import os

        sim = os.environ.get("HELMET_LOCKER_SIM_UID", "04:SIM:TEST:01")
        time.sleep(1)
        return sim

    reader = _init_reader()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        (status, _) = reader.MFRC522_Request(reader.PICC_REQIDL)
        if status != reader.MI_OK:
            time.sleep(poll_interval)
            continue
        (status, uid) = reader.MFRC522_Anticoll()
        if status == reader.MI_OK and uid:
            uid_hex = _uid_to_hex(uid)
            reader.MFRC522_StopCrypto1()
            logger.info("RFID read: %s", uid_hex)
            return uid_hex
        time.sleep(poll_interval)
    return None


def wait_for_tag(message: str = "Tap RFID card...") -> str | None:
    logger.info(message)
    return read_uid()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Hold RFID tag near reader (Ctrl+C to quit)...")
    try:
        while True:
            uid = read_uid(timeout_sec=5)
            if uid:
                print("UID:", uid)
    except KeyboardInterrupt:
        print("Stopped.")
