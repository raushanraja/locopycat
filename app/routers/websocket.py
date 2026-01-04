from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64
import secrets
import hashlib
from app.security import (
    check_client_authorized, 
    server_public_key, 
    server_private_key, 
    AUTHORIZED_CLIENTS_FILE
)
from app.connection_manager import manager

router = APIRouter()

@router.websocket("/ws")
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
