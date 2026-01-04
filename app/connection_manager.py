from typing import List
from fastapi import WebSocket
import json
import secrets
import hashlib
import base64
from app.security import cycle_key

# Track active WebSocket connections with authentication
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[tuple[WebSocket, bytes]] = []  # (websocket, shared_secret)
        self.client_public_keys: dict = {}  # client_id -> public_key
    
    async def connect(self, websocket: WebSocket, client_id: str, shared_secret: bytes):
        self.active_connections.append((websocket, shared_secret))
        print(f"Client {client_id} connected")
    
    def disconnect(self, websocket: WebSocket):
        for conn in self.active_connections:
            if conn[0] == websocket:
                self.active_connections.remove(conn)
                print("Client disconnected")
                break
    
    async def broadcast(self, message: dict):
        encrypted_messages = {}
        
        # Encrypt message for each client separately
        for websocket, shared_secret in self.active_connections:
            try:
                # Convert message to JSON and encrypt with shared secret
                message_json = json.dumps(message)
                # Simple XOR encryption as example (in production, use AES)
                shared_key = shared_secret[:32] if len(shared_secret) >= 32 else shared_secret.ljust(32, b'\0')
                iv = secrets.token_bytes(16)
                
                # HMAC for message integrity
                hmac = hashlib.sha256(shared_key + iv + message_json.encode()).digest()
                
                # XOR encryption (replace with AES in production)
                encrypted = bytes([a ^ b ^ iv[i % len(iv)] for i, (a, b) in enumerate(zip(message_json.encode(), cycle_key(shared_key, len(message_json))))])
                
                payload = {
                    "iv": base64.b64encode(iv).decode(),
                    "hmac": base64.b64encode(hmac).decode(),
                    "data": base64.b64encode(encrypted).decode()
                }
                
                await websocket.send_json(payload)
            except Exception as e:
                print(f"Failed to send to client: {e}")
                try:
                    self.active_connections.remove((websocket, shared_secret))
                except:
                    pass

manager = ConnectionManager()
