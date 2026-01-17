#!/bin/bash
# Install Locopycat Client as a systemd user service
# This will start the client automatically when you log in

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SCRIPT_DIR/locopycat-client.service"

echo "=========================================="
echo "Locopycat Client systemd Service Installer"
echo "=========================================="
echo ""

# Check if we're being run from the project directory
if [ ! -f "$PROJECT_DIR/client.py" ]; then
    echo "ERROR: Cannot find client.py in $PROJECT_DIR"
    echo "Please run this script from the install/linux/ directory"
    exit 1
fi

# Get the current user
USERNAME=$(whoami)
USER_HOME=$(eval echo ~$USERNAME)

echo "Installation directory: $PROJECT_DIR"
echo "Username: $USERNAME"
echo "Home directory: $USER_HOME"
echo ""

# Create systemd user directory if it doesn't exist
USER_SYSTEMD_DIR="$USER_HOME/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

# Check if service already exists
SERVICE_PATH="$USER_SYSTEMD_DIR/locopycat-client.service"
if [ -f "$SERVICE_PATH" ]; then
    echo "Service file already exists at:"
    echo "  $SERVICE_PATH"
    echo ""
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# Copy and configure the service file
echo "Installing service file..."
sed -e "s|%h|$USER_HOME|g" "$SERVICE_FILE" > "$SERVICE_PATH"

# Enable and start the service
echo "Enabling service..."
systemctl --user daemon-reload
systemctl --user enable locopycat-client.service

echo ""
echo "=========================================="
echo "Installation successful!"
echo "=========================================="
echo ""
echo "The locopycat client will now start automatically when you log in."
echo ""
echo "To control the service:"
echo "  Start now:     systemctl --user start locopycat-client"
echo "  Stop:          systemctl --user stop locopycat-client"
echo "  Restart:       systemctl --user restart locopycat-client"
echo "  View status:   systemctl --user status locopycat-client"
echo "  View logs:     journalctl --user -u locopycat-client -f"
echo ""
echo "You can also run 'python client.py' manually for debugging."
