# LoCopyCat - Modular Service Architecture

## Overview

LoCopyCat provides a secure, encrypted WebSocket broadcasting infrastructure that supports multiple independent services running simultaneously on the same server. Each service can receive data via API endpoints and broadcast to its subscribed WebSocket clients without interfering with other services.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                           │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Shared Security Layer                         │ │
│  │  - RSA Key Exchange                                        │ │
│  │  - Client Authorization                                    │ │
│  │  - Encrypted Communication (HMAC verified)                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐   │
│  │  Service: Copy  │  │ Service: Notify │  │ Service: ...  │   │
│  ├─────────────────┤  ├─────────────────┤  ├───────────────┤   │
│  │ API:            │  │ API:            │  │ API:          │   │
│  │ /api/clipboard  │  │ /api/notify     │  │ /api/...      │   │
│  │                 │  │                 │  │               │   │
│  │ Channel: copy   │  │ Channel: notify │  │ Channel: ...  │   │
│  │                 │  │                 │  │               │   │
│  │ Clients: []     │  │ Clients: []     │  │ Clients: []   │   │
│  └─────────────────┘  └─────────────────┘  └───────────────┘   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              WebSocket Endpoint: /ws                       │ │
│  │  - Handshake with channel subscription                     │ │
│  │  - Route messages to appropriate service handlers          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Encrypted WebSocket
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ Client  │          │ Client  │          │ Client  │
   │ (copy)  │          │ (notify)│          │ (multi) │
   └─────────┘          └─────────┘          └─────────┘
```

## Core Concepts

### 1. Services (Channels)

Each service represents an independent functionality:
- **Clipboard** - Copy text/images to clipboard
- **Notifications** - Display system notifications
- **Logs** - Centralized logging
- **Commands** - Remote command execution
- **Custom** - Your own service logic

Services are isolated:
- Each has its own API endpoint
- Each manages its own client subscriptions
- Messages only broadcast to subscribed clients
- Services share the same security infrastructure

### 2. Connection Manager

The `ConnectionManager` tracks clients and their channel subscriptions:

```python
class ConnectionManager:
    def __init__(self):
        # Structure: {websocket: {
        #   'shared_secret': bytes,
        #   'client_id': str,
        #   'channels': ['copy', 'notify', ...]
        # }}
        self.active_connections: dict = {}
    
    async def broadcast(self, message: dict, channel: str):
        """Broadcast message only to clients subscribed to the channel."""
        # Encrypts and sends to subscribed clients only
```

### 3. Message Protocol

All messages follow a standard envelope:

```json
{
  "channel": "service-name",
  "action": "action-type",
  "data": { /* service-specific payload */ },
  "timestamp": 1234567890,
  "message_id": "unique-id"
}
```

**Examples:**

```json
// Clipboard service
{
  "channel": "clipboard",
  "action": "copy",
  "data": {
    "type": "text",
    "content": "Hello World"
  }
}

// Notification service
{
  "channel": "notify",
  "action": "show",
  "data": {
    "title": "Alert",
    "message": "Server restarting in 5 minutes",
    "level": "warning"
  }
}

// Logging service
{
  "channel": "logs",
  "action": "append",
  "data": {
    "level": "error",
    "source": "web-server",
    "message": "Database connection failed"
  }
}
```

### 4. Client Subscription

Clients subscribe to channels during WebSocket handshake:

```python
# Client connects and specifies channels
init_message = {
    "client_id": "my-laptop",
    "public_key": "<RSA-public-key>",
    "channels": ["clipboard", "notify"]  # Subscribe to multiple
}
```

### 5. API Endpoints

Each service exposes its own API endpoint:

```
POST /api/clipboard - Broadcast clipboard data
POST /api/notify    - Send notifications
POST /api/logs      - Forward logs
POST /api/execute   - Send commands
```

## Security Model

All services share the same security infrastructure:

1. **Authentication**: Client authorization via RSA public key fingerprints
2. **Key Exchange**: Secure key exchange using RSA encryption
3. **Encryption**: All messages encrypted with per-client shared secrets
4. **Integrity**: HMAC verification prevents message tampering
5. **Isolation**: Channel-based routing ensures message privacy

## File Structure

```
app/
├── main.py                      # FastAPI app initialization
├── connection_manager.py        # Multi-channel connection manager
├── security.py                  # Shared security functions
├── routers/
│   ├── websocket.py            # WebSocket endpoint with channel support
│   ├── api.py                  # Legacy API (deprecated)
│   └── services/               # Service-specific routers
│       ├── __init__.py
│       ├── clipboard.py        # Clipboard service API
│       ├── notify.py           # Notification service API
│       ├── logs.py             # Logging service API
│       └── custom.py           # Your custom service
└── clients/
    ├── clipboard_client.py     # Clipboard client
    ├── notify_client.py        # Notification client
    ├── logs_client.py          # Logging client
    └── base_client.py          # Shared client base class
```

## Benefits

1. **Modularity**: Add new services without modifying existing ones
2. **Scalability**: Services scale independently
3. **Flexibility**: Clients can subscribe to multiple services
4. **Isolation**: Service failures don't affect others
5. **Reusability**: Share security and connection infrastructure
6. **Maintainability**: Clear separation of concerns

## Migration Path

### From Current (Single-Service)
```
/api/print → /ws → All clients (clipboard action only)
```

### To Modular (Multi-Service)
```
/api/clipboard → /ws (channel: clipboard) → Subscribed clients
/api/notify    → /ws (channel: notify)    → Subscribed clients
/api/logs      → /ws (channel: logs)      → Subscribed clients
```

Both can coexist during migration for backward compatibility.

## Next Steps

1. Read [SERVICE_CREATION_GUIDE.md](SERVICE_CREATION_GUIDE.md) to create your first service
2. Review [EXAMPLES.md](EXAMPLES.md) for common service implementations
3. Check [API_REFERENCE.md](API_REFERENCE.md) for detailed API documentation
