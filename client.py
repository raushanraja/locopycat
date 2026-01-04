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
import os
import secrets
import hashlib
import base64
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


def cycle_key(key: bytes, length: int) -> bytes:
    """Cycle the key to match required length."""
    return (key * ((length // len(key)) + 1))[:length]


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
    return await websockets.connect(SERVER_URL)


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
    
    # Generate client keys
    client_private_key, client_public_key = generate_client_keys()
    client_id = f"client_{secrets.token_hex(8)}"
    
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
            await websocket.send_json({
                "client_id": client_id,
                "public_key": client_public_key_pem.decode()
            })
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
            await websocket.send_json({
                "encrypted_secret": base64.b64encode(client_encrypted_secret).decode()
            })
            
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
