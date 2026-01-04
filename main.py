from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
import json
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hashlib
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables with defaults
AUTHORIZED_CLIENTS_FILE = os.getenv("AUTHORIZED_CLIENTS_FILE", "authorized_clients.txt")
SERVER_PRIVATE_KEY = os.getenv("SERVER_PRIVATE_KEY", "server_private.pem")
SERVER_PUBLIC_KEY = os.getenv("SERVER_PUBLIC_KEY", "server_public.pem")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))

app = FastAPI()

# Generate RSA key pair for server
def generate_server_keys():
    """Generate or load server RSA key pair."""
    private_key_path = SERVER_PRIVATE_KEY
    public_key_path = SERVER_PUBLIC_KEY
    
    # Check if keys already exist
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        print("Loading existing server keys...")
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
    print("Generating new server keys...")
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
    
    print("Server keys generated and saved")
    return private_key, public_key

# Initialize server keys
server_private_key, server_public_key = generate_server_keys()

def load_authorized_clients() -> Dict[str, str]:
    """Load authorized client public keys from file.
    
    Returns dict mapping fingerprint to client_id.
    """
    authorized_keys = {}
    if os.path.exists(AUTHORIZED_CLIENTS_FILE):
        with open(AUTHORIZED_CLIENTS_FILE, 'r') as f:
            content = f.read().strip()
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Check if this is the new format (base64 with ::)
                if '::' in line:
                    parts = line.split('::', 1)
                    if len(parts) == 2:
                        client_id, encoded_key = parts
                        try:
                            public_key_pem = base64.b64decode(encoded_key).decode()
                            # Generate fingerprint from public key
                            public_key = serialization.load_pem_public_key(
                                public_key_pem.encode(),
                                backend=default_backend()
                            )
                            public_key_bytes = public_key.public_bytes(
                                encoding=serialization.Encoding.DER,
                                format=serialization.PublicFormat.SubjectPublicKeyInfo
                            )
                            fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[:16]
                            authorized_keys[fingerprint] = client_id
                        except Exception as e:
                            print(f"Warning: Failed to load key for {client_id}: {e}")
                # Old format (single line with :)
                elif ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        client_id, public_key_pem = parts
                        # Replace literal \n with actual newlines
                        public_key_pem = public_key_pem.replace('\\n', '\n')
                        try:
                            public_key = serialization.load_pem_public_key(
                                public_key_pem.encode(),
                                backend=default_backend()
                            )
                            public_key_bytes = public_key.public_bytes(
                                encoding=serialization.Encoding.DER,
                                format=serialization.PublicFormat.SubjectPublicKeyInfo
                            )
                            fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[:16]
                            authorized_keys[fingerprint] = client_id
                        except Exception as e:
                            print(f"Warning: Failed to load key for {client_id}: {e}")
    return authorized_keys


def check_client_authorized(public_key_pem: str) -> tuple[bool, str]:
    """Check if a client's public key is authorized."""
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[:16]
        
        authorized = load_authorized_clients()
        if fingerprint in authorized:
            return True, authorized[fingerprint]
        
        return False, fingerprint
    except Exception as e:
        print(f"Error checking authorization: {e}")
        return False, "invalid"


# Load authorized clients on startup
authorized_clients = load_authorized_clients()
print(f"Loaded {len(authorized_clients)} authorized client(s)")

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

def cycle_key(key: bytes, length: int) -> bytes:
    """Cycle the key to match required length."""
    return (key * ((length // len(key)) + 1))[:length]

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Paste & Print</title>
    </head>
    <body>
        <h2>Paste Something</h2>
        <form method="post" action="/print">
            <textarea name="content" rows="10" cols="50"></textarea><br><br>
            <button type="submit">Print on Server</button>
        </form>
    </body>
    </html>
    """

@app.post("/print")
async def print_content(request: Request):
    form = await request.form()
    content = form.get("content")
    print("===== Received Content (HTML Form) =====")
    print(content)
    print("======================================")
    
    # Broadcast to all connected WebSocket clients
    if content:
        await manager.broadcast({"action": "copy", "content": content})
        print(f"Content broadcasted to {len(manager.active_connections)} client(s)")
    
    return {"status": "printed", "broadcasted": len(manager.active_connections)}


@app.get("/server-public-key")
async def get_server_public_key():
    """Return the server's public key for clients to use."""
    public_key_pem = server_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return {"public_key": public_key_pem.decode()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = None
    shared_secret = None
    
    # Accept the WebSocket connection first
    await websocket.accept()
    
    try:
        # Step 1: Receive client's public key
        try:
            init_message = await websocket.receive_json()
        except Exception as e:
            await websocket.close(code=4008, reason="Invalid initial message")
            print(f"Connection rejected: Failed to receive initial message: {e}")
            return
        
        client_id = init_message.get("client_id", "unknown")
        client_public_key_pem = init_message.get("public_key")
        
        if not client_public_key_pem:
            await websocket.close(code=4008, reason="Public key required")
            print(f"Connection rejected: No public key provided")
            return
        
        # Step 1.5: Check if client is authorized
        is_authorized, fingerprint = check_client_authorized(client_public_key_pem)
        if not is_authorized:
            await websocket.close(code=4003, reason="Unauthorized client")
            print(f"Connection rejected: Unauthorized client (fingerprint: {fingerprint})")
            print(f"   To authorize this client, add its public key to {AUTHORIZED_CLIENTS_FILE}")
            print(f"   Or use: python manage_clients.py add <client_public_key.pem>")
            return
        
        # Load client's public key
        try:
            client_public_key = serialization.load_pem_public_key(
                client_public_key_pem.encode(),
                backend=default_backend()
            )
        except Exception as e:
            await websocket.close(code=4008, reason="Invalid public key")
            print(f"Connection rejected: Invalid public key format")
            return
        
        print(f"Authorized client attempting connection: {fingerprint}")
        
        # Step 2: Send server's public key
        server_public_key_pem = server_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        await websocket.send_json({
            "server_public_key": server_public_key_pem.decode()
        })
        
        # Step 3: Generate shared secret using Diffie-Hellman-like exchange
        # For simplicity, we'll use RSA to exchange a secret
        server_secret = secrets.token_bytes(32)
        encrypted_secret = client_public_key.encrypt(
            server_secret,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                    label=None
                )
            )
        
        await websocket.send_json({
            "encrypted_secret": base64.b64encode(encrypted_secret).decode()
        })
        
        # Step 4: Receive client's encrypted secret
        response = await websocket.receive_json()
        client_encrypted_secret = base64.b64decode(response.get("encrypted_secret"))
        
        try:
            client_secret = server_private_key.decrypt(
                client_encrypted_secret,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                label=None
            )
        )
        except Exception as e:
            await websocket.close(code=4008, reason="Authentication failed")
            print(f"Error decrypting client secret: {e}")
            return
        
        # Step 5: Derive shared secret from both secrets
        shared_secret = hashlib.sha256(server_secret + client_secret).digest()
        
        # Send confirmation
        await websocket.send_json({
            "status": "authenticated",
            "client_id": client_id
        })
        
        print(f"Client {client_id} authenticated successfully")
        
        # Connect authenticated client
        await manager.connect(websocket, client_id, shared_secret)
        
        # Main loop - receive and respond to keepalive pings
        while True:
            try:
                message = await websocket.receive_text()
                # Client should send ping messages periodically
            except WebSocketDisconnect:
                raise
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client {client_id} disconnected")
    except HTTPException as e:
        print(f"Client {client_id} HTTP error: {e}")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Client {client_id} connection error: {e}")
        import traceback
        traceback.print_exc()
        manager.disconnect(websocket)


@app.post("/api/print")
async def api_print(payload: dict):
    content = payload.get("content")
    print("===== Received Content (API) =====")
    print(content)
    print("===============================")
    
    # Broadcast to all connected WebSocket clients
    if content:
        await manager.broadcast({"action": "copy", "content": content})
        print(f"Content broadcasted to {len(manager.active_connections)} client(s)")
    
    return {"status": "printed", "broadcasted": len(manager.active_connections), "length": len(content) if content else 0}

# Run with: uvicorn main:app --reload
