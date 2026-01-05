#!/usr/bin/env python3
"""
WebSocket client for locopycat server.
Connects to the server and copies received text/images to the local clipboard.
"""

import asyncio
import websockets
import pyperclip
import json
import sys
import os
import secrets
import hashlib
import base64
import subprocess
import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
try:
    import io
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Configure logging for retry attempts
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server configuration
SERVER_URL = "ws://localhost:8000/ws"  # Change this if server is on different host

# Configuration for retry
MAX_RETRIES = 10  # Maximum number of connection attempts
MIN_WAIT = 2      # Minimum wait time in seconds
MAX_WAIT = 60     # Maximum wait time in seconds

# Keys directory
KEYS_DIR = ".keys"

# Image save directory configuration
# Can be overridden via environment variable LOCOPYCAT_IMAGE_DIR
IMAGE_SAVE_DIR = os.getenv("LOCOPYCAT_IMAGE_DIR", "received_images")

# Whether to save images to disk (even when clipboard copy succeeds)
SAVE_IMAGES = os.getenv("LOCOPYCAT_SAVE_IMAGES", "true").lower() == "true"


def cycle_key(key: bytes, length: int) -> bytes:
    """Cycle the key to match required length."""
    return (key * ((length // len(key)) + 1))[:length]


def setup_image_dir():
    """Create the image save directory if it doesn't exist."""
    if not os.path.exists(IMAGE_SAVE_DIR):
        os.makedirs(IMAGE_SAVE_DIR)
        print(f"Created image save directory: {IMAGE_SAVE_DIR}")


def save_image(image_data: bytes, mime_type: str = "image/png") -> str:
    """Save image data to disk and return the file path."""
    setup_image_dir()
    
    # Determine file extension from MIME type
    mime_to_ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp"
    }
    
    ext = mime_to_ext.get(mime_type.lower(), ".png")
    
    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Remove last digit for millisecond precision
    filename = f"image_{timestamp}{ext}"
    filepath = os.path.join(IMAGE_SAVE_DIR, filename)
    
    # Write image data
    with open(filepath, "wb") as f:
        f.write(image_data)
    
    print(f"   Image saved to: {filepath}")
    return filepath


def generate_client_keys():
    """Generate or load client RSA key pair."""
    if not os.path.exists(KEYS_DIR):
        os.makedirs(KEYS_DIR)
    
    private_key_path = os.path.join(KEYS_DIR, "client_private.pem")
    public_key_path = os.path.join(KEYS_DIR, "client_public.pem")
    
    # Check if keys already exist
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        print("Loading existing client keys...")
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        return private_key, public_key
    
    # Generate new keys
    print("Generating new client keys...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    
    # Save keys
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    
    print("Client keys generated and saved")
    return private_key, public_key


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
    retry=retry_if_exception_type((ConnectionRefusedError, ConnectionResetError, OSError)),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.INFO)
)
async def connect_with_retry():
    """Connect to WebSocket server with exponential backoff retry."""
    # Increase max_size to 50MB (52428800 bytes) to handle large images
    return await websockets.connect(SERVER_URL, max_size=52428800)


async def decrypt_message(encrypted_payload: dict, shared_secret: bytes) -> dict:
    """Decrypt a message from the server."""
    try:
        # Decode components
        iv = base64.b64decode(encrypted_payload["iv"])
        hmac_received = base64.b64decode(encrypted_payload["hmac"])
        data = base64.b64decode(encrypted_payload["data"])
        
        # Prepare shared key
        shared_key = shared_secret[:32] if len(shared_secret) >= 32 else shared_secret.ljust(32, b'\0')
        
        # Decrypt using XOR (replace with AES in production)
        decrypted = bytes([a ^ b ^ iv[i % len(iv)] for i, (a, b) in enumerate(zip(data, cycle_key(shared_key, len(data))))])
        
        # Verify HMAC
        message_str = decrypted.decode()
        expected_hmac = hashlib.sha256(shared_key + iv + message_str.encode()).digest()
        
        if not secrets.compare_digest(hmac_received, expected_hmac):
            raise ValueError("HMAC verification failed")
        
        return json.loads(message_str)
    except Exception as e:
        print(f"Decryption error: {e}")
        return {}


async def handle_messages(websocket, shared_secret):
    """Handle incoming messages from the WebSocket server."""
    while True:
        try:
            message = await websocket.recv()
            payload = json.loads(message)
            
            # Decrypt if encrypted payload
            if "data" in payload and "iv" in payload and "hmac" in payload:
                data = await decrypt_message(payload, shared_secret)
            else:
                data = payload
            
            if data.get("action") == "copy":
                content_type = data.get("type", "text")
                content = data.get("content", "")
                
                if content_type == "image":
                    print(f"Received image ({len(content)} bytes base64 encoded)")
                    mime_type = data.get("mime_type", "image/png")
                    print(f"   MIME Type: {mime_type}")
                    
                    try:
                        # Decode base64
                        image_data = base64.b64decode(content)
                        print(f"   Decoded size: {len(image_data)} bytes")
                        
                        # Save image to disk (if enabled)
                        if SAVE_IMAGES:
                            saved_path = save_image(image_data, mime_type)
                        else:
                            saved_path = None
                        
                        if PIL_AVAILABLE:
                            img = Image.open(io.BytesIO(image_data))
                            
                            if sys.platform == 'darwin':
                                # macOS - use osascript to copy image
                                import tempfile
                                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                                    tmp_path = tmp.name
                                    if img.mode in ('RGBA', 'LA', 'P'):
                                        img = img.convert('RGBA') if img.mode != 'RGBA' else img.convert('RGB')
                                    if img.mode == 'RGBA':
                                        # Create white background
                                        background = Image.new('RGBA', img.size, (255, 255, 255, 255))
                                        background.paste(img, mask=img.split()[3])
                                        img = background
                                    img.save(tmp_path, format='PNG')
                                
                                os.system(f'osascript -e \'set the clipboard to (read file "POSIX file://{tmp_path}" as «class PNGf»)\'')
                                os.unlink(tmp_path)
                                print("Image copied to clipboard!\n")
                                
                            elif sys.platform == 'win32':
                                # Windows - use PyWin32 if available, otherwise try clipboard
                                try:
                                    import win32clipboard
                                    import tempfile
                                    
                                    with tempfile.NamedTemporaryFile(suffix='.dib', delete=False) as tmp:
                                        tmp_path = tmp.name
                                        # Convert to DIB format for Windows clipboard
                                        output = io.BytesIO()
                                        if img.mode != 'RGB':
                                            img = img.convert('RGB')
                                        img.save(output, format='BMP')
                                        # Remove BMP header (14 bytes) to get DIB
                                        dib_data = output.getvalue()[14:]
                                        tmp.write(dib_data)
                                        tmp.close()
                                    
                                    win32clipboard.OpenClipboard()
                                    win32clipboard.EmptyClipboard()
                                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
                                    win32clipboard.CloseClipboard()
                                    os.unlink(tmp_path)
                                    print("Image copied to clipboard!\n")
                                except ImportError:
                                    # PyWin32 not available, try alternative
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                                        tmp_path = tmp.name
                                        img.save(tmp_path, format='PNG')
                                    subprocess.Popen(['powershell', '-Command', f'Set-Clipboard -Path "{tmp_path}"'], shell=True)
                                    print("Image copied to clipboard! (via PowerShell)\n")
                                except Exception as e:
                                    print(f"Failed to copy image on Windows: {e}")
                                    raise
                                    
                            elif sys.platform.startswith('linux'):
                                # Linux - try xclip with image support
                                import tempfile
                                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                                    tmp_path = tmp.name
                                    img.save(tmp_path, format='PNG')
                                
                                # Try xclip with image support
                                try:
                                    # Run xclip in the background - it may stay alive to maintain clipboard
                                    subprocess.Popen(
                                        ['xclip', '-selection', 'clipboard', '-t', 'image/png', '-i', tmp_path],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL
                                    )
                                    print("Image copied to clipboard!\n")
                                except FileNotFoundError:
                                    print("Note: Image clipboard support requires xclip")
                                    print(f"Image saved to: {tmp_path}")
                                    print("Install xclip: sudo apt-get install xclip\n")
                                except Exception as e:
                                    print(f"Note: Failed to copy image to clipboard: {e}")
                                    print(f"Image saved to: {tmp_path}\n")
                                finally:
                                    # Clean up temp file after a short delay
                                    import threading
                                    def cleanup_tmp():
                                        import time
                                        time.sleep(0.5)  # Give xclip time to read the file
                                        try:
                                            os.unlink(tmp_path)
                                        except:
                                            pass
                                    threading.Thread(target=cleanup_tmp, daemon=True).start()
                            else:
                                print(f"Platform {sys.platform} not supported for image clipboard")
                        else:
                            # PIL not installed - print error
                            if not saved_path:
                                print("Note: PIL/Pillow not installed. Install it for image clipboard support:")
                                print("      pip install pillow")
                                print("")
                                
                    except Exception as e:
                        print(f"Failed to copy image to clipboard: {e}\n")
                        import traceback
                        traceback.print_exc()
                else:
                    # Text content
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
    
    # Setup image save directory
    setup_image_dir()
    
    # Generate client keys
    client_private_key, client_public_key = generate_client_keys()
    client_id = f"client-{secrets.token_hex(8)}"
    
    while retry_count < max_reconnect_attempts or max_reconnect_attempts == -1:
        try:
            if retry_count == 0:
                print(f"Connecting to server: {SERVER_URL}")
            else:
                print(f"Reconnecting... (attempt {retry_count})")
            
            websocket = await connect_with_retry()
            
            # Step 1: Send client public key
            client_public_key_pem = client_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            await websocket.send(json.dumps({
                "client_id": client_id,
                "public_key": client_public_key_pem.decode()
            }))
            print("Initiating authentication...")
            
            # Step 2: Receive server public key
            server_public_key_message = await websocket.recv()
            server_public_key_data = json.loads(server_public_key_message)
            server_public_key = serialization.load_pem_public_key(
                server_public_key_data["server_public_key"].encode(),
                backend=default_backend()
            )
            
            # Step 3: Receive encrypted server secret
            server_secret_message = await websocket.recv()
            server_secret_data = json.loads(server_secret_message)
            server_encrypted_secret = base64.b64decode(server_secret_data["encrypted_secret"])
            
            # Decrypt server secret
            server_secret = client_private_key.decrypt(
                server_encrypted_secret,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Step 4: Generate and send client secret
            client_secret = secrets.token_bytes(32)
            client_encrypted_secret = server_public_key.encrypt(
                client_secret,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            await websocket.send(json.dumps({
                "encrypted_secret": base64.b64encode(client_encrypted_secret).decode()
            }))
            
            # Step 5: Derive shared secret
            shared_secret = hashlib.sha256(server_secret + client_secret).digest()
            
            # Receive authentication confirmation
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            if auth_data.get("status") == "authenticated":
                print(f"Authenticated as {auth_data.get('client_id')}")
                print("Connected! Listening for clipboard updates...")
                print("   Press Ctrl+C to disconnect\n")
                retry_count = 0  # Reset retry count on successful connection
            else:
                raise websockets.exceptions.ConnectionClosed(4008, "Authentication failed")
            
            await handle_messages(websocket, shared_secret)
        
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
