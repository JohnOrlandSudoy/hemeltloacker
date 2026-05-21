"""
Helmet Locker — central configuration.
Adjust paths and pins for your Raspberry Pi wiring.
"""
import os
from pathlib import Path

# --- GPIO (BCM numbering) ---
PIN_SOLENOID = 17
PIN_RFID_RST = 25

# --- Serial (AS608 fingerprint) ---
# On Pi: enable serial hardware, disable login shell → /dev/serial0
FINGERPRINT_PORT = "/dev/serial0"
FINGERPRINT_BAUD = 57600
FINGERPRINT_PASSWORD = 0xFFFFFFFF
FINGERPRINT_ADDRESS = 0xFFFFFFFF

# --- Unlock behavior ---
UNLOCK_DURATION_SEC = 3
UNLOCK_DEBOUNCE_SEC = 5
UNLOCK_POLICY = "any_one"  # any_one | two_of_three | all_three

# --- Face recognition ---
FACE_TOLERANCE = 0.5
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
FACE_CAPTURE_FRAMES = 5

# --- RFID ---
RFID_SPI_BUS = 0
RFID_SPI_DEVICE = 0

# --- Data storage ---
# On Pi use /var/lib/helmetlocker; locally use project data dir
if os.path.exists("/var/lib/helmetlocker") or os.environ.get("HELMET_LOCKER_PI"):
    DATA_ROOT = Path("/var/lib/helmetlocker")
else:
    DATA_ROOT = Path(__file__).resolve().parent / "data"

DB_PATH = DATA_ROOT / "users.db"
FACES_DIR = DATA_ROOT / "faces"
LOG_PATH = DATA_ROOT / "access.log"

# --- Admin ---
ADMIN_PIN = "1234"

# --- Simulation (Windows dev / no hardware) ---
SIMULATE_HARDWARE = os.environ.get("HELMET_LOCKER_SIMULATE", "").lower() in (
    "1",
    "true",
    "yes",
) or os.name == "nt"

# --- UI ---
APP_TITLE = "Helmet Locker"
FULLSCREEN = True
