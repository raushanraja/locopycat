from fastapi import APIRouter
from cryptography.hazmat.primitives import serialization
from app.security import server_public_key
from app.connection_manager import manager

router = APIRouter()

@router.get("/server-public-key")
async def get_server_public_key():
    """Return the server's public key for clients to use."""
    public_key_pem = server_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return {"public_key": public_key_pem.decode()}

@router.post("/api/print")
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
