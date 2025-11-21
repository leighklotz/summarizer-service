#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
UNIT_DEST="$HOME/.config/systemd/user"

echo "Installing summarizer-service systemd user unit..."

# Enable lingering so user services run at boot before login
echo "Enabling systemd user lingering for $USER..."
sudo loginctl enable-linger "$USER"

# Install the unit
mkdir -p "$UNIT_DEST"
echo "Copying summarizer-service.service to $UNIT_DEST/"
cp "$SCRIPT_DIR/summarizer-service.service" "$UNIT_DEST/summarizer-service.service"

# Reload user systemd, enable & start service
echo "Reloading user systemd daemon..."
systemctl --user daemon-reload

echo "Enabling summarizer-service.service for autostart..."
systemctl --user enable summarizer-service.service

echo "Starting summarizer-service.service..."
systemctl --user start summarizer-service.service

echo
echo "Installation complete."
echo
echo "Check service status:"
echo "  systemctl --user status summarizer-service.service"
echo
echo "Check logs:"
echo "  journalctl --user -u summarizer-service.service -e"
echo
