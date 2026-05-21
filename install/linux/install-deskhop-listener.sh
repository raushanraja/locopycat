#!/bin/bash
# Install Locopycat DeskHop Listener as a systemd user service
# This will start the listener automatically when you log in

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"  # Go up from install/linux/ to project root
SERVICE_FILE="$SCRIPT_DIR/locopycat-deskhop-listener.service"

echo "=========================================="
echo "Locopycat DeskHop Listener Service Installer"
echo "=========================================="
echo ""

# Check if we're being run from the project directory
if [ ! -f "$PROJECT_DIR/deskhop_listener.py" ]; then
    echo "ERROR: Cannot find deskhop_listener.py in $PROJECT_DIR"
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

# Check if the listener script is executable
if [ ! -x "$PROJECT_DIR/deskhop_listener.py" ]; then
    echo "Making deskhop_listener.py executable..."
    chmod +x "$PROJECT_DIR/deskhop_listener.py"
fi

# Create systemd user directory if it doesn't exist
USER_SYSTEMD_DIR="$USER_HOME/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

# Check if service already exists
SERVICE_PATH="$USER_SYSTEMD_DIR/locopycat-deskhop-listener.service"
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
systemctl --user enable locopycat-deskhop-listener.service

echo ""
echo "=========================================="
echo "Installation successful!"
echo "=========================================="
echo ""
echo "The DeskHop listener will now start automatically when you log in."
echo ""
echo "IMPORTANT: Ensure your user has read access to /dev/hidraw* devices."
echo "  Run: sudo usermod -a -G input $USER && log out and back in"
echo ""
echo "To control the service:"
echo "  Start now:     systemctl --user start locopycat-deskhop-listener"
echo "  Stop:          systemctl --user stop locopycat-deskhop-listener"
echo "  Restart:       systemctl --user restart locopycat-deskhop-listener"
echo "  View status:   systemctl --user status locopycat-deskhop-listener"
echo "  View logs:     journalctl --user -u locopycat-deskhop-listener -f"
echo ""
echo "To set a custom server URL:"
echo "  systemctl --user edit locopycat-deskhop-listener"
echo "  Then add under [Service]:"
echo "    Environment=LOCOPYCAT_SERVER_URL=http://192.168.1.100:8000"
echo ""
echo "You can also run the listener directly for debugging:"
echo "  LOCOPYCAT_SERVER_URL=http://localhost:8000 ./deskhop_listener.py"
