# Service Creation Guide

This guide walks you through creating a new service in the LoCopyCat modular architecture.

## Quick Start

Creating a new service involves 3 steps:

1. **Create Service API Router** - Define API endpoints
2. **Create Service Client** - Handle received messages
3. **Register Service** - Add to server configuration

## Step 1: Create Service API Router

Create a new file: `app/routers/services/your_service.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.connection_manager import manager
from typing import Optional
import time

router = APIRouter()

# Define request model
class YourServiceRequest(BaseModel):
    # Define your service-specific fields
    data: dict
    priority: Optional[str] = "normal"

@router.post("/api/your-service")
async def your_service_endpoint(request: YourServiceRequest):
    """
    Receive data via API and broadcast to subscribed WebSocket clients.
    """
    print(f"===== Your Service: Received Data =====")
    print(f"Data: {request.data}")
    print(f"Priority: {request.priority}")
    print("=" * 40)
    
    # Prepare message for broadcast
    message = {
        "channel": "your-service",  # Channel identifier
        "action": "process",         # Action type
        "data": request.data,        # Service-specific data
        "priority": request.priority,
        "timestamp": int(time.time()),
        "message_id": f"{int(time.time() * 1000)}"
    }
    
    # Broadcast to all clients subscribed to "your-service" channel
    broadcast_count = await manager.broadcast(message, channel="your-service")
    
    print(f"Broadcasted to {broadcast_count} client(s)")
    
    return {
        "status": "success",
        "channel": "your-service",
        "clients_notified": broadcast_count,
        "message_id": message["message_id"]
    }

@router.get("/api/your-service/status")
async def your_service_status():
    """
    Get status of your service (optional endpoint).
    """
    # Count clients subscribed to your channel
    subscribed_clients = sum(
        1 for conn_data in manager.active_connections.values()
        if "your-service" in conn_data.get("channels", [])
    )
    
    return {
        "channel": "your-service",
        "subscribed_clients": subscribed_clients,
        "status": "operational"
    }
```

### Key Points:

- **Channel Name**: Use consistent `"your-service"` identifier
- **Message Structure**: Follow the standard envelope (channel, action, data)
- **Broadcasting**: Use `manager.broadcast(message, channel="your-service")`
- **Error Handling**: Add try/except for production use

## Step 2: Create Service Client

Create a new file: `clients/your_service_client.py`

```python
#!/usr/bin/env python3
"""
Client for your-service channel.
Connects to server and processes received messages.
"""

import asyncio
import websockets
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.base_client import BaseClient

class YourServiceClient(BaseClient):
    """
    Client that subscribes to 'your-service' channel.
    """
    
    def __init__(self, server_url: str):
        super().__init__(
            server_url=server_url,
            channels=["your-service"],  # Subscribe to your channel
            client_id="your-service-client"
        )
    
    async def handle_message(self, message: dict):
        """
        Handle messages received on subscribed channels.
        
        Args:
            message: Decrypted message dict
        """
        channel = message.get("channel")
        action = message.get("action")
        data = message.get("data", {})
        
        if channel != "your-service":
            return  # Ignore messages from other channels
        
        print(f"\n===== Received on {channel} channel =====")
        print(f"Action: {action}")
        print(f"Data: {json.dumps(data, indent=2)}")
        print("=" * 40)
        
        # Process based on action
        if action == "process":
            await self.process_data(data)
        else:
            print(f"Unknown action: {action}")
    
    async def process_data(self, data: dict):
        """
        Your service-specific processing logic.
        
        Args:
            data: The data payload to process
        """
        # Implement your service logic here
        print(f"Processing data: {data}")
        
        # Example: Save to file, display notification, execute command, etc.
        # ...

def main():
    """Main entry point."""
    # Configure your server URL
    SERVER_URL = os.getenv("LOCOPYCAT_SERVER", "ws://localhost:8030/ws")
    
    print(f"Starting Your Service Client")
    print(f"Server: {SERVER_URL}")
    print(f"Channels: your-service")
    print("-" * 40)
    
    client = YourServiceClient(SERVER_URL)
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nClient stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

### Key Points:

- **Inherit from BaseClient**: Reuse authentication, encryption, reconnection logic
- **Subscribe to Channel**: Set `channels=["your-service"]` in constructor
- **Handle Messages**: Override `handle_message()` to process your data
- **Idempotent**: Client should handle duplicate messages gracefully

## Step 3: Register Service

### 3.1 Register Router in Main App

Edit `app/main.py`:

```python
from fastapi import FastAPI
from app.routers import web, websocket
from app.routers.services import clipboard, notify, your_service  # Add your service

app = FastAPI()

# Include routers
app.include_router(web.router)
app.include_router(websocket.router)
app.include_router(clipboard.router)
app.include_router(notify.router)
app.include_router(your_service.router)  # Register your service
```

### 3.2 Update Connection Manager (if needed)

If you need custom per-channel logic, edit `app/connection_manager.py`:

```python
async def broadcast(self, message: dict, channel: str):
    """Broadcast message to clients subscribed to the channel."""
    
    # Optional: Add channel-specific preprocessing
    if channel == "your-service":
        # Custom logic for your service
        message["processed"] = True
    
    # ... rest of broadcast logic
```

## Step 4: Test Your Service

### 4.1 Start Server

```bash
make docker-up
# Or locally:
make run-server
```

### 4.2 Start Client

```bash
python clients/your_service_client.py
```

### 4.3 Send Test Message

```bash
curl -X POST http://localhost:8030/api/your-service \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "message": "Hello from your service"
    },
    "priority": "high"
  }'
```

You should see:
- Server logs the received data
- Client receives and processes the message
- Response confirms broadcast success

## Advanced Features

### Multi-Action Support

Handle multiple action types in your client:

```python
async def handle_message(self, message: dict):
    action = message.get("action")
    data = message.get("data", {})
    
    actions = {
        "create": self.handle_create,
        "update": self.handle_update,
        "delete": self.handle_delete,
    }
    
    handler = actions.get(action)
    if handler:
        await handler(data)
    else:
        print(f"Unknown action: {action}")
```

### Request/Response Pattern

Implement acknowledgments:

```python
# Server side
message = {
    "channel": "your-service",
    "action": "process",
    "data": data,
    "requires_ack": True,
    "request_id": "req-12345"
}

# Client side
async def handle_message(self, message: dict):
    # Process message
    await self.process_data(message["data"])
    
    # Send acknowledgment if required
    if message.get("requires_ack"):
        await self.send_ack(message["request_id"])
```

### Filtering and Targeting

Send to specific clients:

```python
# Add client metadata during connection
# Then filter in broadcast:

message = {
    "channel": "your-service",
    "action": "process",
    "target_client_id": "specific-client",  # Optional targeting
    "data": data
}

# Connection manager filters by target_client_id
```

## Best Practices

1. **Validate Input**: Use Pydantic models for API validation
2. **Error Handling**: Wrap client logic in try/except
3. **Logging**: Use proper logging instead of print()
4. **Idempotency**: Include message IDs to detect duplicates
5. **Documentation**: Document your message formats
6. **Testing**: Write unit tests for handlers
7. **Security**: Validate data before processing on client
8. **Graceful Degradation**: Handle missing dependencies

## Common Patterns

### Pattern 1: Simple Notification Service

```python
# API: POST /api/notify
# Message: {"channel": "notify", "action": "show", "data": {"title": "...", "message": "..."}}
# Client: Display system notification
```

### Pattern 2: Data Collection Service

```python
# API: POST /api/metrics
# Message: {"channel": "metrics", "action": "collect", "data": {"cpu": 45, "memory": 82}}
# Client: Store metrics in local database
```

### Pattern 3: Command Execution Service

```python
# API: POST /api/execute
# Message: {"channel": "execute", "action": "run", "data": {"command": "ls -la"}}
# Client: Execute command and optionally send result back
```

## Troubleshooting

### Clients not receiving messages?

1. Check client is subscribed to correct channel
2. Verify channel name matches in API and client
3. Check client connection status in logs
4. Ensure message format is correct

### Broadcasting fails?

1. Verify `manager.broadcast()` is awaited
2. Check channel parameter is provided
3. Ensure ConnectionManager is imported correctly
4. Review encryption/decryption errors in logs

### Service conflicts?

1. Use unique channel names
2. Check for duplicate router registration
3. Verify API endpoints don't overlap
4. Review connection manager channel isolation

## Next Steps

- Review [EXAMPLES.md](EXAMPLES.md) for complete service examples
- Check [API_REFERENCE.md](API_REFERENCE.md) for detailed API docs
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system overview
