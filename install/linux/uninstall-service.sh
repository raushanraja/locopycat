#!/bin/bash
# Remove Locopycat Client systemd user service

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=========================================="
echo "Locopycat Client Service Uninstaller"
echo "=========================================="
echo ""

# Get the current user
USERNAME=$(whoami)
USER_HOME=$(eval echo ~$USERNAME)
SERVICE_PATH="$USER_HOME/.config/systemd/user/locopycat-client.service"

if [ ! -f "$SERVICE_PATH" ]; then
    echo "Service file not found at:"
    echo "  $SERVICE_PATH"
    echo "Nothing to do."
    exit 0
fi

echo "This will remove the locopycat client systemd service."
echo ""
read -p "Are you sure? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# Stop and disable the service
echo "Stopping service..."
systemctl --user stop locopycat-client.service 2>/dev/null || true

echo "Disabling service..."
systemctl --user disable locopycat-client.service 2>/dev/null || true

# Remove the service file
echo "Removing service file..."
rm -f "$SERVICE_PATH"

# Reload systemd
systemctl --user daemon-reload

echo ""
echo "=========================================="
echo "Uninstallation successful!"
echo "=========================================="
echo ""
echo "The locopycat client will no longer start automatically."
echo "You can still run 'python client.py' manually."
