#!/bin/bash
# One-time Raspberry Pi setup for Helmet Locker
set -e

echo "=== Helmet Locker Pi setup ==="

sudo apt update
sudo apt install -y \
  python3-pip python3-venv \
  python3-dev \
  libatlas-base-dev \
  cmake \
  libopenblas-dev \
  libjpeg-dev \
  zlib1g-dev \
  libhdf5-dev \
  libharfbuzz0b \
  libwebp7 \
  tcl8.6-dev tk8.6-dev \
  git

# Enable SPI and serial (manual reminder)
echo ""
echo "Run: sudo raspi-config"
echo "  - Interface Options -> SPI -> Enable"
echo "  - Interface Options -> Serial -> Login shell NO, Serial hardware YES"
echo ""

# Data directory
sudo mkdir -p /var/lib/helmetlocker/faces
sudo chown -R "$USER:$USER" /var/lib/helmetlocker

# Groups for GPIO/SPI
sudo usermod -aG spi,gpio,dialout "$USER" 2>/dev/null || true

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$HOME/helmetlocker-venv"

python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Autostart
mkdir -p "$HOME/.config/autostart"
sed "s|/home/pi/helmetlocker|$PROJECT_DIR|g; s|/home/pi/helmetlocker-venv|$VENV|g" \
  "$PROJECT_DIR/deploy/helmetlocker.desktop" > "$HOME/.config/autostart/helmetlocker.desktop"

export HELMET_LOCKER_PI=1
echo ""
echo "Setup complete. Reboot, then run:"
echo "  source $VENV/bin/activate"
echo "  cd $PROJECT_DIR"
echo "  python main.py"
