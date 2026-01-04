#!/usr/bin/env python3
"""
WebSocket client for locopycat server.
Connects to the server and copies received text to the local clipboard.
"""

import asyncio
import websockets
import pyperclip
import json
import sys
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

# Configure logging for retry attempts
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server configuration
SERVER_URL = "ws://localhost:8000/ws"  # Change this if server is on different host

# Configuration for retry
MAX_RETRIES = 10  # Maximum number of connection attempts
MIN_WAIT = 2      # Minimum wait time in seconds
MAX_WAIT = 60     # Maximum wait time in seconds


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
    retry=retry_if_exception_type((ConnectionRefusedError, ConnectionResetError, OSError)),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.INFO)
)
async def connect_with_retry():
    """Connect to WebSocket server with exponential backoff retry."""
    return await websockets.connect(SERVER_URL)


async def handle_messages(websocket):
    """Handle incoming messages from the WebSocket server."""
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("action") == "copy":
                content = data.get("content", "")
                print(f"Received content ({len(content)} chars)")
                print(f"   Content: {content[:50]}{'...' if len(content) > 50 else ''}")
                
                try:
                    pyperclip.copy(content)
                    print("Copied to clipboard!\n")
                except Exception as e:
                    print(f"Failed to copy to clipboard: {e}\n")
                    print(f"   Tip: On Linux, ensure xclip or xsel is installed")
                    print(f"        sudo apt-get install xclip  # Debian/Ubuntu")
                    print(f"        sudo dnf install xclip     # Fedora\n")
        
        except websockets.exceptions.ConnectionClosed:
            raise  # Re-raise to trigger reconnection
        except json.JSONDecodeError as e:
            print(f"Failed to parse message: {e}\n")


async def clipboard_client():
    """Connect to WebSocket server and handle clipboard operations with auto-reconnect."""
    retry_count = 0
    max_reconnect_attempts = -1  # -1 means infinite reconnection attempts
    
    while retry_count < max_reconnect_attempts or max_reconnect_attempts == -1:
        try:
            if retry_count == 0:
                print(f"Connecting to server: {SERVER_URL}")
            else:
                print(f"Reconnecting... (attempt {retry_count})")
            
            websocket = await connect_with_retry()
            print("Connected! Listening for clipboard updates...")
            print("   Press Ctrl+C to disconnect\n")
            retry_count = 0  # Reset retry count on successful connection
            
            await handle_messages(websocket)
        
        except ConnectionRefusedError:
            if retry_count < MAX_RETRIES - 1:
                print(f"Connection refused. Retrying in {min(2 ** retry_count, MAX_WAIT)} seconds...")
                retry_count += 1
                await asyncio.sleep(min(2 ** retry_count, MAX_WAIT))
            else:
                print(f"Connection refused after {MAX_RETRIES} attempts.")
                print(f"   Is the server running?")
                print(f"   Server URL: {SERVER_URL}")
                sys.exit(1)
        
        except (ConnectionResetError, OSError, websockets.exceptions.ConnectionClosed) as e:
            print(f"Connection lost: {e}")
            if retry_count < MAX_RETRIES - 1:
                print(f"Reconnecting in {min(2 ** retry_count, MAX_WAIT)} seconds...")
                retry_count += 1
                await asyncio.sleep(min(2 ** retry_count, MAX_WAIT))
            else:
                print(f"Failed to reconnect after {MAX_RETRIES} attempts. Exiting.")
                sys.exit(1)
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            if retry_count < MAX_RETRIES - 1:
                print(f"Retrying in {min(2 ** retry_count, MAX_WAIT)} seconds...")
                retry_count += 1
                await asyncio.sleep(min(2 ** retry_count, MAX_WAIT))
            else:
                print(f"Failed after {MAX_RETRIES} attempts. Exiting.")
                sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(clipboard_client())
    except KeyboardInterrupt:
        print("\n\nDisconnected cleanly")
