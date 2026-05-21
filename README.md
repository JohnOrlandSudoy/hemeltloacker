# Helmet Locker System (Raspberry Pi 4)

Multi-factor helmet locker: **fingerprint (AS608)** + **RFID (RC522)** + **face (USB webcam)**. Only registered users can open the **12V solenoid** lock via a relay. Touch UI runs on a **7" HDMI capacitive display**.

## Hardware

| Part | Interface |
|------|-----------|
| Raspberry Pi 4 Model B | — |
| 7" HDMI capacitive LCD | HDMI + USB touch |
| AS608 fingerprint | UART (GPIO 14/15) |
| RC522 RFID | SPI |
| USB 1080p webcam | USB |
| 12V solenoid + relay module | GPIO 17 + 12V supply |

## Wiring diagram (BCM)

```
                    Raspberry Pi 4
                 ┌─────────────────────┐
    3.3V ────────┤ 1                   │
    5V   ────────┤ 2  (relay VCC)      │
                 │                     │
    AS608 TX ────┤ 10 GPIO15 RXD       │
    AS608 RX ────┤ 8  GPIO14 TXD       │
    GND  ────────┤ 6                   │
                 │                     │
    RC522 SDA ───┤ 24 GPIO8  CE0       │
    RC522 SCK ───┤ 23 GPIO11           │
    RC522 MOSI ──┤ 19 GPIO10           │
    RC522 MISO ──┤ 21 GPIO9            │
    RC522 RST ───┤ 22 GPIO25           │
    RC522 3.3V ──┤ 1                   │
                 │                     │
    Relay IN ────┤ 11 GPIO17           │
    Relay GND ───┤ 6                   │
    Relay VCC ───┤ 2  5V               │
                 └─────────────────────┘

    Relay COM/NO ── 12V+ ── Solenoid ── 12V-
    (Flyback diode 1N4007 across solenoid coil)
```

**Important**

- RC522 **3.3V only** (not 5V).
- AS608: module **TX → Pi RX (GPIO15)**, module **RX → Pi TX (GPIO14)**.
- Never power the solenoid from the Pi 5V pin — use a separate **12V** supply.
- Common **GND** between Pi, relay, and 12V supply.

## Raspberry Pi OS setup

### 1. Flash and boot

1. Install **Raspberry Pi OS (64-bit)** with Raspberry Pi Imager.
2. Enable SSH/Wi‑Fi in imager if needed.
3. Boot with display (HDMI) and USB touch connected.

### 2. Enable interfaces

```bash
sudo raspi-config
```

- **Interface Options → SPI → Enable**
- **Interface Options → Serial Port → Login shell: No, Serial hardware: Yes**

Reboot after changes.

### 3. Install project

Copy this folder to the Pi, e.g. `~/helmetlocker`:

```bash
cd ~/helmetlocker
chmod +x scripts/setup_pi.sh
./scripts/setup_pi.sh
```

Or manually:

```bash
sudo mkdir -p /var/lib/helmetlocker/faces
sudo chown -R $USER:$USER /var/lib/helmetlocker
sudo usermod -aG spi,gpio,dialout $USER

python3 -m venv ~/helmetlocker-venv
source ~/helmetlocker-venv/bin/activate
pip install -r requirements.txt
```

`face_recognition` may take **30–60+ minutes** to build on the Pi.

### 4. Autostart on boot

```bash
cp deploy/helmetlocker.desktop ~/.config/autostart/
# Edit paths in the .desktop file if your install dir differs
```

Set in `~/.profile` or autostart:

```bash
export HELMET_LOCKER_PI=1
export KIVY_GL_BACKEND=gl
```

### 5. Run

```bash
source ~/helmetlocker-venv/bin/activate
cd ~/helmetlocker
export HELMET_LOCKER_PI=1
python main.py
```

## Test each module (before full app)

```bash
source ~/helmetlocker-venv/bin/activate
cd ~/helmetlocker
export HELMET_LOCKER_PI=1

python -m hardware.solenoid    # relay click ~3s
python -m hardware.rfid        # tap card, prints UID
python -m hardware.fingerprint # enroll or search
python -m hardware.camera      # face encoding test
```

## Using the app

1. **Register User** — enter name → fingerprint (2 scans) → RFID tap → face at webcam.
2. **Unlock Locker** — fingerprint button, face button, or tap RFID (background listen on unlock screen).
3. **Admin** — default PIN `1234` (change in `config.py`) → list/delete users.

Unlock policy (default): **any one** of fingerprint, RFID, or face (`UNLOCK_POLICY = "any_one"` in `config.py`).

## Configuration

Edit [`config.py`](config.py):

| Setting | Default | Description |
|---------|---------|-------------|
| `PIN_SOLENOID` | 17 | Relay control GPIO |
| `PIN_RFID_RST` | 25 | RC522 reset |
| `FINGERPRINT_PORT` | `/dev/serial0` | AS608 serial |
| `UNLOCK_DURATION_SEC` | 3 | Solenoid pulse length |
| `UNLOCK_POLICY` | `any_one` | `any_one`, `two_of_three`, `all_three` |
| `FACE_TOLERANCE` | 0.5 | Lower = stricter face match |
| `ADMIN_PIN` | `1234` | Change in production |
| `DB_PATH` | `/var/lib/helmetlocker/users.db` | When `HELMET_LOCKER_PI=1` |

## Project layout

```
helmetlocker/
├── main.py              # Start UI
├── config.py
├── requirements.txt
├── database/db.py       # SQLite users + logs
├── hardware/            # Drivers
├── services/            # Register + unlock logic
├── ui/                  # Kivy screens
├── deploy/              # Autostart .desktop
└── scripts/setup_pi.sh
```

## Windows development (simulation)

No Pi hardware required — uses simulated sensors:

```powershell
cd helmetlocker
$env:HELMET_LOCKER_SIMULATE="1"
python -m hardware.solenoid
python -m database.db
```

Optional env vars:

- `HELMET_LOCKER_SIM_UID` — simulated RFID UID
- `HELMET_LOCKER_SIM_FP` — simulated fingerprint position

## Troubleshooting

| Problem | Fix |
|---------|-----|
| RC522 not reading | Enable SPI; 3.3V power; `groups` shows `spi`; retry wiring |
| AS608 silent | Swap TX/RX; `ls -l /dev/serial0`; user in `dialout` group |
| Permission denied serial | `sudo usermod -aG dialout $USER` then reboot |
| Relay not clicking | GPIO 17; 5V to relay; active-HIGH vs LOW jumper on module |
| Face not recognized | Better lighting; re-register; lower `FACE_TOLERANCE` slightly |
| Kivy black screen | `export KIVY_GL_BACKEND=gl`; run from desktop session not SSH-only |
| Solenoid weak | Bigger 12V supply; check diode; shorter `UNLOCK_DURATION_SEC` |

## Security notes

Suitable for school/project lockers, not high-security facilities. Change `ADMIN_PIN`, backup `/var/lib/helmetlocker/users.db`, and re-enroll fingerprints if you replace the AS608 module.

## License

MIT — use and modify for your capstone/project.
