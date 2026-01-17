# Automatic Startup Installation

This guide explains how to configure the locopycat client to start automatically when your computer boots or when you log in.

## Linux Installation (systemd)

For modern Linux distributions (Ubuntu 18.04+, Fedora, Debian, Arch, etc.), the recommended method is to use a systemd user service.

### Quick Installation

```bash
cd /path/to/locopycat/install/linux
chmod +x install-service.sh uninstall-service.sh
./install-service.sh
```

### What This Does

- Creates a systemd user service that starts the locopycat client
- Enables the service to start automatically when you log in
- Configures the service to restart automatically if it crashes
- Starts the service immediately after installation

### Managing the Service

After installation, you can manage the service using these commands:

```bash
# Start/Stop/Restart the service
systemctl --user start locopycat-client
systemctl --user stop locopycat-client
systemctl --user restart locopycat-client

# Check service status
systemctl --user status locopycat-client

# View real-time logs
journalctl --user -u locopycat-client -f

# Check if service is enabled to start at login
systemctl --user is-enabled locopycat-client
```

### Troubleshooting

**Service won't start:**
```bash
# Check the logs for errors
journalctl --user -u locopycat-client -n 50
```

**Python not found:**
If the service fails because Python is not at `/usr/bin/python3`, edit the service file:
```bash
nano ~/.config/systemd/user/locopycat-client.service
```
Change `ExecStart=/usr/bin/python3` to your actual Python path (check with `which python3`).

**DISPLAY variable issues:**
Make sure you have a display available. The service includes `Environment=DISPLAY=:0` but you may need to adjust this for your setup.

### Uninstalling

```bash
cd /path/to/locopycat/install/linux
./uninstall-service.sh
```

---

## Windows Installation

For Windows, you can add the client to the Windows Startup folder.

### Quick Installation

1. **As administrator**, run the installer:
   ```cmd
   cd C:\path\to\locopycat\install\windows
   install-startup.bat
   ```

2. **Or manually add to startup:**
   - Press `Win + R`, type `shell:startup`, and press Enter
   - Create a shortcut to `start-locopycat.bat` in that folder
   - Or right-click `start-locopycat.bat`, select "Create shortcut", then move the shortcut to the startup folder

### What This Does

- Creates a shortcut in your Windows Startup folder
- The client will start automatically after you log into Windows
- Uses `start-locopycat.bat` which handles error messages and checks for Python

### Manual Startup

You can also run the client manually at any time:
```cmd
cd C:\path\to\locopycat
start-locopycat.bat
```

### Uninstalling

Run the uninstaller (as recommended user):
```cmd
cd C:\path\to\locopycat\install\windows
uninstall-startup.bat
```

Or manually:
- Press `Win + R`, type `shell:startup`, and press Enter
- Delete the "Locopycat Client" shortcut

---

## Alternative: Desktop Autostart (Linux Desktop Environments)

For desktop environments like GNOME, KDE, XFCE, etc.:

1. Copy the desktop entry file (create one if needed):
   ```bash
   # For user-level autostart
   mkdir -p ~/.config/autostart
   # You would need to create a .desktop file pointing to your client.py
   ```

2. Add a script to your desktop's autostart settings through the GUI:
   - Go to Settings → Session and Startup → Application Autostart
   - Add an entry with the command: `python3 /path/to/locopycat/client.py`

---

## Testing the Installation

After installing automatic startup, it's a good idea to test that everything works:

### Linux
```bash
# Check if service is running
systemctl --user status locopycat-client

# Restart your computer and check if the client started automatically
systemctl --user status locopycat-client
journalctl --user -u locopycat-client --since "5 minutes ago"
```

### Windows
```cmd
# Run the client manually first
start-locopycat.bat

# Restart your computer and check if the client window opened
# Also check Task Manager for python.exe processes
```

---

## Common Issues

### Python not found in PATH (Windows)
Make sure Python is installed and added to your system PATH:
1. Download Python from https://www.python.org/
2. During installation, check "Add Python to PATH"
3. Restart your computer
4. Verify with `python --version` in Command Prompt

### Dependencies not installed
Make sure all required packages are installed:
```bash
# Linux
pip install -r requirements.txt

# Windows
python -m pip install -r requirements.txt
```

### Permissions issues (Linux)
Make sure the script is executable and you have ownership of the files:
```bash
chmod +x client.py
# Run as your regular user, not as root/sudo
```

---

## System-Wide Startup (Linux - For Servers)

If you want the client to start even when no user is logged in (not typically needed for clipboard access), you can install it as a system service:

```bash
# Install system-wide (requires sudo)
sudo cp install/linux/locopycat-client.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable locopycat-client
sudo systemctl start locopycat-client
```

Note: This is typically not recommended for the client as clipboard access usually requires a user session and display.
