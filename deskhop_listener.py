#!/usr/bin/env python3
"""
DeskHop-to-LoCopyCat clipboard bridge.

Monitors the DeskHop KVM switch keyboard HID interface for Ctrl+C/X
presses AND polls the local clipboard for changes. When new content
is detected, pushes it to the locopycat server API for broadcasting
to connected clients.

Works with the stock DeskHop firmware (CFG_TUD_HID=2) which does not
expose a separate vendor HID interface.

Requires:
  - pyperclip (with xclip/xsel on Linux, or wl-clipboard on Wayland)
  - Read access to /dev/hidraw* (add user to 'input' group)
  - DISPLAY=:0 or similar when running under X11 for clipboard access

Usage:
  LOCOPYCAT_SERVER_URL=http://192.168.1.100:8000 ./deskhop_listener.py
"""

import hashlib
import json
import logging
import os
import select
import sys
import time
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

import pyperclip

# ── Configuration ──────────────────────────────────────────────────────

SERVER_URL = os.getenv("LOCOPYCAT_SERVER_URL", "http://localhost:8000").rstrip("/")
API_ENDPOINT = f"{SERVER_URL}/api/print"
CLIPBOARD_POLL_INTERVAL = float(os.getenv("LOCOPYCAT_CLIPBOARD_POLL", "0.5"))
HID_POLL_TIMEOUT = 1.0
DEVICE_RETRY_INTERVAL = 5.0

# DeskHop USB identity
DESKHOP_VID = 0x2e8a
DESKHOP_PID = 0x107c

# HID keyboard report layout
RID_KEYBOARD = 1
IDX_MODIFIER = 1
IDX_KEYCODES = 3
KEYCODE_C = 0x06
KEYCODE_X = 0x1B
MOD_LCTRL = 0x01
MOD_RCTRL = 0x10

# Logging
logging.basicConfig(
    level=os.getenv("LOCOPYCAT_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("deskhop-bridge")


# ── HID device discovery ───────────────────────────────────────────────

def _read_sysfs(path: str) -> Optional[str]:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _is_deskhop_device(syspath: str) -> bool:
    modalias = (
        _read_sysfs(f"{syspath}/device/modalias")
        or _read_sysfs(f"{syspath}/device/../modalias")
        or ""
    )
    upper = modalias.upper()
    return f"{DESKHOP_VID:04X}" in upper and f"{DESKHOP_PID:04X}" in upper


def find_keyboard_device() -> Optional[str]:
    """Find the DeskHop keyboard HID interface by checking the report
    descriptor for keyboard usage (Usage Page 1, Usage 6)."""
    for entry in sorted(os.listdir("/sys/class/hidraw/")):
        hidraw_path = f"/dev/{entry}"
        syspath = f"/sys/class/hidraw/{entry}"
        if not _is_deskhop_device(syspath):
            continue
        try:
            with open(f"{syspath}/device/report_descriptor", "rb") as f:
                desc = f.read()
        except OSError:
            continue
        if b"\x05\x01\x09\x06" in desc:
            return hidraw_path
    return None


# ── HID report parsing ─────────────────────────────────────────────────

def has_ctrl_c_or_x(report: bytes) -> bool:
    """Return True if this HID keyboard report contains Ctrl+C or Ctrl+X."""
    if len(report) < IDX_KEYCODES + 6 or report[0] != RID_KEYBOARD:
        return False
    if not (report[IDX_MODIFIER] & (MOD_LCTRL | MOD_RCTRL)):
        return False
    keycodes = report[IDX_KEYCODES:IDX_KEYCODES + 6]
    return KEYCODE_C in keycodes or KEYCODE_X in keycodes


# ── API caller ─────────────────────────────────────────────────────────

def send_to_api(content: str) -> bool:
    """Send clipboard content to the locopycat /api/print endpoint."""
    payload = json.dumps({"content": content, "type": "text"}).encode()
    req = Request(
        API_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return True
            log.warning("API returned HTTP %d", resp.status)
            return False
    except (URLError, OSError) as e:
        log.warning("API request failed: %s", e)
        return False


# ── Main loop ──────────────────────────────────────────────────────────

def main():
    log.info("DeskHop-to-LoCopyCat bridge starting")
    log.info("Server URL: %s", SERVER_URL)
    log.info("API endpoint: %s", API_ENDPOINT)

    last_content_hash = ""
    last_clipboard_check = 0.0
    fd = None
    poll_obj = select.poll()

    try:
        while True:
            # ── Open HID device if not connected ──────────────────────
            if fd is None:
                device_path = find_keyboard_device()
                if device_path is None:
                    log.info("DeskHop not found, retrying in %.0fs...", DEVICE_RETRY_INTERVAL)
                    time.sleep(DEVICE_RETRY_INTERVAL)
                    continue

                log.info("Opening keyboard HID: %s", device_path)
                try:
                    fd = os.open(device_path, os.O_RDONLY | os.O_NONBLOCK)
                    poll_obj.register(fd, select.POLLIN)
                except OSError as e:
                    log.warning("Cannot open %s: %s", device_path, e)
                    log.warning("Try: sudo usermod -a -G input $USER && log out")
                    fd = None
                    time.sleep(DEVICE_RETRY_INTERVAL)
                    continue

            # ── Poll for HID reports ──────────────────────────────────
            try:
                events = poll_obj.poll(int(HID_POLL_TIMEOUT * 1000))
            except KeyboardInterrupt:
                raise

            # ── Path 1: HID keyboard trigger (Ctrl+C/X) ──────────────
            if events:
                try:
                    raw = os.read(fd, 64)
                except OSError:
                    log.info("Device disconnected, reconnecting...")
                    poll_obj.unregister(fd)
                    os.close(fd)
                    fd = None
                    continue

                if has_ctrl_c_or_x(raw):
                    try:
                        content = pyperclip.paste()
                    except Exception as e:
                        log.warning("Failed to read clipboard: %s", e)
                        continue

                    content_hash = hashlib.sha256(content.encode()).hexdigest()
                    if content_hash == last_content_hash or not content:
                        continue
                    last_content_hash = content_hash

                    log.info(
                        "Ctrl+%s detected! Sending %d chars to API...",
                        "X" if KEYCODE_X in raw[IDX_KEYCODES:IDX_KEYCODES + 6] else "C",
                        len(content),
                    )
                    if send_to_api(content):
                        log.info("Sent successfully")
                    else:
                        log.info("Send failed (will retry on next event)")

            # ── Path 2: Clipboard polling ─────────────────────────────
            now = time.monotonic()
            if now - last_clipboard_check >= CLIPBOARD_POLL_INTERVAL:
                last_clipboard_check = now
                try:
                    content = pyperclip.paste()
                except Exception as e:
                    log.warning("Failed to read clipboard: %s", e)
                    continue

                content_hash = hashlib.sha256(content.encode()).hexdigest()
                if content_hash == last_content_hash or not content:
                    continue
                last_content_hash = content_hash

                log.info("Clipboard changed! Sending %d chars to API...", len(content))
                if send_to_api(content):
                    log.info("Sent successfully")
                else:
                    log.info("Send failed (will retry on next event)")

    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        if fd is not None:
            poll_obj.unregister(fd)
            os.close(fd)

    return 0


if __name__ == "__main__":
    sys.exit(main())
