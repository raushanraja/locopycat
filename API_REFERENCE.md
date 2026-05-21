# API Reference

Complete API documentation for the LoCopyCat modular service architecture.

## Table of Contents

1. [Connection Manager API](#connection-manager-api)
2. [WebSocket Protocol](#websocket-protocol)
3. [Base Client API](#base-client-api)
4. [Security API](#security-api)
5. [Service API Pattern](#service-api-pattern)

---

## Connection Manager API

The `ConnectionManager` class handles all WebSocket connections and message broadcasting with channel isolation.

### Class: `ConnectionManager`

Located in: `app/connection_manager.py`

#### Attributes

```python
active_connections: dict
```
Dictionary mapping WebSocket connections to their metadata:
```python
{
    websocket: {
        'shared_secret': bytes,      # Encryption key
        'client_id': str,            # Client identifier
        'channels': List[str],       # Subscribed channels
        'connected_at': float,       # Connection timestamp
        'metadata': dict             # Custom metadata
    }
}
```

#### Methods

##### `async connect(websocket: WebSocket, client_id: str, shared_secret: bytes, channels: List[str])`

Register a new authenticated WebSocket connection.

**Parameters:**
- `websocket` (WebSocket): The WebSocket connection object
- `client_id` (str): Unique identifier for the client
- `shared_secret` (bytes): Encryption key derived during handshake
- `channels` (List[str]): List of channels client subscribes to

**Returns:** None

**Example:**
```python
await manager.connect(
    websocket=websocket,
    client_id="laptop-001",
    shared_secret=b"...",
    channels=["clipboard", "notify"]
)
```

---

##### `disconnect(websocket: WebSocket)`

Remove a disconnected client.

**Parameters:**
- `websocket` (WebSocket): The WebSocket to disconnect

**Returns:** None

**Example:**
```python
manager.disconnect(websocket)
```

---

##### `async broadcast(message: dict, channel: str) -> int`

Broadcast a message to all clients subscribed to a specific channel.

**Parameters:**
- `message` (dict): The message payload (will be encrypted per client)
- `channel` (str): The channel to broadcast on

**Returns:** `int` - Number of clients that received the message

**Message Structure:**
```python
{
    "channel": str,           # Channel identifier (required)
    "action": str,            # Action type (required)
    "data": dict,            # Service-specific payload (required)
    "timestamp": int,        # Unix timestamp (optional)
    "message_id": str,       # Unique message ID (optional)
    "priority": str,         # Priority level (optional)
    "requires_ack": bool,    # Requires acknowledgment (optional)
}
```

**Example:**
```python
count = await manager.broadcast(
    message={
        "channel": "notify",
        "action": "show",
        "data": {"title": "Alert", "message": "System update"}
    },
    channel="notify"
)
print(f"Notified {count} clients")
```

---

##### `get_channel_clients(channel: str) -> List[dict]`

Get list of clients subscribed to a specific channel.

**Parameters:**
- `channel` (str): Channel name

**Returns:** `List[dict]` - List of client metadata dictionaries

**Example:**
```python
clients = manager.get_channel_clients("clipboard")
for client in clients:
    print(f"Client: {client['client_id']}")
```

---

##### `get_client_channels(client_id: str) -> List[str]`

Get list of channels a specific client is subscribed to.

**Parameters:**
- `client_id` (str): Client identifier

**Returns:** `List[str]` - List of channel names

**Example:**
```python
channels = manager.get_client_channels("laptop-001")
print(f"Subscribed to: {', '.join(channels)}")
```

---

## WebSocket Protocol

### Connection Handshake

The WebSocket endpoint (`/ws`) implements a secure handshake protocol.

#### 1. Client → Server: Initial Connection

```json
{
    "client_id": "my-laptop",
    "public_key": "-----BEGIN PUBLIC KEY-----\n...",
    "channels": ["clipboard", "notify", "logs"]
}
```

#### 2. Server → Client: Server Public Key

```json
{
    "server_public_key": "-----BEGIN PUBLIC KEY-----\n..."
}
```

#### 3. Server → Client: Encrypted Secret

```json
{
    "encrypted_secret": "base64-encoded-encrypted-data"
}
```

#### 4. Client → Server: Encrypted Client Secret

```json
{
    "encrypted_secret": "base64-encoded-encrypted-data"
}
```

#### 5. Authentication Complete

Connection established. Both parties derive shared secret for message encryption.

### Message Format (Encrypted)

All messages after handshake are encrypted:

```json
{
    "iv": "base64-encoded-initialization-vector",
    "hmac": "base64-encoded-message-authentication-code",
    "data": "base64-encoded-encrypted-payload"
}
```

### Message Format (Decrypted Payload)

After decryption, the payload structure:

```json
{
    "channel": "service-name",
    "action": "action-type",
    "data": {
        // Service-specific data
    },
    "timestamp": 1234567890,
    "message_id": "unique-id"
}
```

---

## Base Client API

Base class for implementing service clients. Handles authentication, encryption, and reconnection.

### Class: `BaseClient`

Located in: `clients/base_client.py`

#### Constructor

```python
def __init__(
    self,
    server_url: str,
    channels: List[str],
    client_id: str = None,
    max_retries: int = 10,
    min_wait: int = 2,
    max_wait: int = 60
)
```

**Parameters:**
- `server_url` (str): WebSocket server URL (e.g., "ws://localhost:8030/ws")
- `channels` (List[str]): List of channels to subscribe to
- `client_id` (str, optional): Client identifier (auto-generated if not provided)
- `max_retries` (int): Maximum connection retry attempts (-1 for infinite)
- `min_wait` (int): Minimum wait time between retries (seconds)
- `max_wait` (int): Maximum wait time between retries (seconds)

**Example:**
```python
class MyClient(BaseClient):
    def __init__(self, server_url: str):
        super().__init__(
            server_url=server_url,
            channels=["my-service"],
            client_id="my-client"
        )
```

#### Abstract Methods (Must Override)

##### `async handle_message(message: dict)`

Handle received messages from subscribed channels.

**Parameters:**
- `message` (dict): Decrypted message dictionary

**Returns:** None

**Example:**
```python
async def handle_message(self, message: dict):
    channel = message.get("channel")
    action = message.get("action")
    data = message.get("data", {})
    
    if channel == "my-service":
        if action == "process":
            await self.process(data)
```

#### Public Methods

##### `async run()`

Start the client (handles connection and message loop).

**Returns:** None (runs until interrupted)

**Example:**
```python
client = MyClient("ws://localhost:8030/ws")
await client.run()
```

---

##### `async send_message(message: dict)`

Send an encrypted message to the server.

**Parameters:**
- `message` (dict): Message to send

**Returns:** None

**Example:**
```python
await self.send_message({
    "channel": "my-service",
    "action": "acknowledge",
    "data": {"message_id": "12345"}
})
```

---

## Security API

Security utilities for authentication and encryption.

### Functions

Located in: `app/security.py`

#### `check_client_authorized(client_public_key_pem: str) -> Tuple[bool, str]`

Check if a client's public key is authorized.

**Parameters:**
- `client_public_key_pem` (str): PEM-encoded RSA public key

**Returns:** `Tuple[bool, str]`
- `bool`: True if authorized, False otherwise
- `str`: SHA256 fingerprint of the public key

**Example:**
```python
from app.security import check_client_authorized

is_auth, fingerprint = check_client_authorized(public_key_pem)
if is_auth:
    print(f"Authorized: {fingerprint}")
```

---

#### `cycle_key(key: bytes, length: int) -> bytes`

Cycle a key to match required length for encryption.

**Parameters:**
- `key` (bytes): The encryption key
- `length` (int): Required length

**Returns:** `bytes` - Key cycled to the specified length

**Example:**
```python
from app.security import cycle_key

key = b"short_key"
extended = cycle_key(key, 256)
```

---

#### Variables

##### `server_public_key: RSAPublicKey`

Server's RSA public key (loaded at startup).

##### `server_private_key: RSAPrivateKey`

Server's RSA private key (loaded at startup).

##### `AUTHORIZED_CLIENTS_FILE: str`

Path to the authorized clients file.

---

## Service API Pattern

Standard pattern for creating service API endpoints.

### Template

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.connection_manager import manager
from typing import Optional
import time

router = APIRouter()

class ServiceRequest(BaseModel):
    # Define your request schema
    data: dict
    # ... additional fields

@router.post("/api/your-service")
async def service_endpoint(request: ServiceRequest):
    """
    Service endpoint documentation.
    
    Example:
        POST /api/your-service
        {
            "data": {...}
        }
    """
    # Validate and process request
    
    # Create message
    message = {
        "channel": "your-service",
        "action": "action-type",
        "data": request.data,
        "timestamp": int(time.time()),
        "message_id": f"msg-{int(time.time() * 1000)}"
    }
    
    # Broadcast to subscribed clients
    count = await manager.broadcast(message, channel="your-service")
    
    # Return response
    return {
        "status": "success",
        "clients_notified": count,
        "message_id": message["message_id"]
    }
```

### Best Practices

1. **Use Pydantic Models**: Validate input with Pydantic
2. **Consistent Naming**: Use kebab-case for channel names
3. **Include Metadata**: Add timestamp and message_id
4. **Error Handling**: Wrap in try/except blocks
5. **Return Count**: Always return number of clients notified
6. **Document Examples**: Include curl examples in docstrings
7. **Log Activity**: Log received data for debugging

### Common Response Format

```json
{
    "status": "success" | "error",
    "clients_notified": 3,
    "message_id": "msg-1234567890",
    "channel": "service-name",
    "error": "error message if status is error"
}
```

---

## Standard Channels

Predefined channels in the base system:

| Channel | Purpose | Actions |
|---------|---------|---------|
| `clipboard` | Clipboard synchronization | `copy` |
| `notify` | System notifications | `show`, `dismiss` |
| `logs` | Centralized logging | `append` |
| `execute` | Command execution | `run` |
| `metrics` | Performance metrics | `collect`, `aggregate` |
| `sync` | File synchronization | `upload`, `download` |

## Error Codes

WebSocket close codes:

| Code | Reason |
|------|--------|
| 4003 | Unauthorized client (public key not in allow list) |
| 4008 | Invalid initial message or public key |
| 1000 | Normal closure |
| 1001 | Going away |

## Rate Limiting

Not implemented by default. Recommended implementation:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/your-service")
@limiter.limit("10/minute")
async def service_endpoint(request: Request, payload: ServiceRequest):
    # ... implementation
```

---

## Version Information

- **API Version**: 2.0.0 (Modular)
- **Protocol Version**: 1.0.0
- **Encryption**: RSA-2048 + XOR (upgrade to AES-256-GCM recommended)
- **HMAC**: SHA-256

---

## Additional Resources

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [SERVICE_CREATION_GUIDE.md](SERVICE_CREATION_GUIDE.md) - Creating new services
- [EXAMPLES.md](EXAMPLES.md) - Complete service examples
- [SECURITY.md](SECURITY.md) - Security documentation
