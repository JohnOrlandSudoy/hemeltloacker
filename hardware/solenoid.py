"""Solenoid lock control via relay on GPIO."""
import logging
import time

import config

logger = logging.getLogger(__name__)

_relay = None


def _get_relay():
    global _relay
    if _relay is not None:
        return _relay
    if config.SIMULATE_HARDWARE:
        logger.info("Solenoid: simulation mode (no GPIO)")
        return None
    from gpiozero import OutputDevice

    _relay = OutputDevice(config.PIN_SOLENOID, active_high=True, initial_value=False)
    return _relay


def pulse(duration_sec: float | None = None) -> None:
    """Energize solenoid for duration, then release."""
    duration = duration_sec if duration_sec is not None else config.UNLOCK_DURATION_SEC
    if config.SIMULATE_HARDWARE:
        logger.info("Solenoid UNLOCK (simulated) for %.1fs", duration)
        time.sleep(min(duration, 0.5))
        return
    relay = _get_relay()
    relay.on()
    logger.info("Solenoid ON for %.1fs", duration)
    time.sleep(duration)
    relay.off()
    logger.info("Solenoid OFF")


def unlock() -> None:
    """Alias for pulse with default duration."""
    pulse()


def cleanup() -> None:
    global _relay
    if _relay is not None:
        _relay.off()
        _relay.close()
        _relay = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing solenoid — relay should click for", config.UNLOCK_DURATION_SEC, "seconds")
    unlock()
    cleanup()
    print("Done.")
