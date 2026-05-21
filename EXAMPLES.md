# Service Examples

Complete, production-ready examples of common services built on the LoCopyCat modular architecture.

## Example 1: Notification Service

Push notifications to all connected devices.

### Server: `app/routers/services/notify.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.connection_manager import manager
from typing import Optional, Literal
import time

router = APIRouter()

class NotificationRequest(BaseModel):
    title: str
    message: str
    level: Literal["info", "warning", "error", "success"] = "info"
    duration: Optional[int] = 5000  # milliseconds
    sound: Optional[bool] = True

@router.post("/api/notify")
async def send_notification(request: NotificationRequest):
    """
    Send a notification to all subscribed clients.
    
    Example:
        POST /api/notify
        {
            "title": "Deployment Complete",
            "message": "Version 2.1.0 is now live",
            "level": "success",
            "duration": 3000
        }
    """
    message = {
        "channel": "notify",
        "action": "show",
        "data": {
            "title": request.title,
            "message": request.message,
            "level": request.level,
            "duration": request.duration,
            "sound": request.sound
        },
        "timestamp": int(time.time()),
        "message_id": f"notify-{int(time.time() * 1000)}"
    }
    
    count = await manager.broadcast(message, channel="notify")
    
    return {
        "status": "sent",
        "clients_notified": count,
        "message_id": message["message_id"]
    }

@router.post("/api/notify/broadcast")
async def broadcast_announcement(title: str, message: str):
    """Quick broadcast endpoint for announcements."""
    request = NotificationRequest(
        title=title,
        message=message,
        level="info",
        sound=False
    )
    return await send_notification(request)
```

### Client: `clients/notify_client.py`

```python
#!/usr/bin/env python3
"""Notification service client - displays system notifications."""

import asyncio
import sys
import os

# Platform-specific notification imports
if sys.platform == 'darwin':
    # macOS - use osascript
    import subprocess
elif sys.platform == 'win32':
    # Windows - use plyer or win10toast
    try:
        from plyer import notification as plyer_notify
    except ImportError:
        plyer_notify = None
elif sys.platform.startswith('linux'):
    # Linux - use notify-send
    import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients.base_client import BaseClient

class NotifyClient(BaseClient):
    """Client that displays system notifications."""
    
    def __init__(self, server_url: str):
        super().__init__(
            server_url=server_url,
            channels=["notify"],
            client_id="notify-client"
        )
    
    async def handle_message(self, message: dict):
        """Handle notification messages."""
        if message.get("channel") != "notify":
            return
        
        action = message.get("action")
        data = message.get("data", {})
        
        if action == "show":
            await self.show_notification(data)
    
    async def show_notification(self, data: dict):
        """Display a system notification."""
        title = data.get("title", "Notification")
        message = data.get("message", "")
        level = data.get("level", "info")
        
        # Map level to icon/urgency
        level_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
        
        icon_prefix = level_map.get(level, "ℹ️")
        display_title = f"{icon_prefix} {title}"
        
        print(f"\n===== Notification =====")
        print(f"Title: {display_title}")
        print(f"Message: {message}")
        print(f"Level: {level}")
        print("=" * 40)
        
        # Platform-specific notification
        try:
            if sys.platform == 'darwin':
                # macOS
                script = f'display notification "{message}" with title "{display_title}"'
                subprocess.run(['osascript', '-e', script])
                
            elif sys.platform == 'win32':
                # Windows
                if plyer_notify:
                    plyer_notify.notify(
                        title=display_title,
                        message=message,
                        timeout=data.get("duration", 5000) // 1000
                    )
                else:
                    print("Install plyer for notifications: pip install plyer")
                    
            elif sys.platform.startswith('linux'):
                # Linux - notify-send
                urgency = "normal"
                if level == "error":
                    urgency = "critical"
                elif level == "warning":
                    urgency = "normal"
                    
                subprocess.run([
                    'notify-send',
                    '-u', urgency,
                    '-t', str(data.get("duration", 5000)),
                    display_title,
                    message
                ])
        except Exception as e:
            print(f"Failed to show notification: {e}")

def main():
    SERVER_URL = os.getenv("LOCOPYCAT_SERVER", "ws://localhost:8030/ws")
    
    print("Starting Notification Client")
    print(f"Server: {SERVER_URL}")
    print("-" * 40)
    
    client = NotifyClient(SERVER_URL)
    asyncio.run(client.run())

if __name__ == "__main__":
    main()
```

### Usage:

```bash
# Start client
python clients/notify_client.py

# Send notification
curl -X POST http://localhost:8030/api/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Build Complete",
    "message": "Your project built successfully",
    "level": "success"
  }'
```

---

## Example 2: Logging Service

Centralized log collection from multiple sources.

### Server: `app/routers/services/logs.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel
from app.connection_manager import manager
from typing import Optional, Literal
import time
import json

router = APIRouter()

class LogEntry(BaseModel):
    level: Literal["debug", "info", "warning", "error", "critical"]
    message: str
    source: str
    context: Optional[dict] = None

@router.post("/api/logs")
async def forward_log(entry: LogEntry):
    """
    Forward log entry to monitoring clients.
    
    Example:
        POST /api/logs
        {
            "level": "error",
            "message": "Database connection failed",
            "source": "web-server-01",
            "context": {"host": "db.example.com", "port": 5432}
        }
    """
    message = {
        "channel": "logs",
        "action": "append",
        "data": {
            "level": entry.level,
            "message": entry.message,
            "source": entry.source,
            "context": entry.context or {},
            "timestamp": int(time.time())
        },
        "timestamp": int(time.time()),
        "message_id": f"log-{int(time.time() * 1000)}"
    }
    
    count = await manager.broadcast(message, channel="logs")
    
    # Also log to server console
    print(f"[{entry.source}] {entry.level.upper()}: {entry.message}")
    if entry.context:
        print(f"   Context: {json.dumps(entry.context)}")
    
    return {
        "status": "logged",
        "clients_notified": count
    }
```

### Client: `clients/logs_client.py`

```python
#!/usr/bin/env python3
"""Logging service client - monitors and saves logs."""

import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients.base_client import BaseClient

class LogsClient(BaseClient):
    """Client that monitors and saves log entries."""
    
    def __init__(self, server_url: str, log_file: str = "received_logs.jsonl"):
        super().__init__(
            server_url=server_url,
            channels=["logs"],
            client_id="logs-client"
        )
        self.log_file = log_file
        
        # Ensure log file exists
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                pass
    
    async def handle_message(self, message: dict):
        """Handle log messages."""
        if message.get("channel") != "logs":
            return
        
        action = message.get("action")
        data = message.get("data", {})
        
        if action == "append":
            await self.save_log(data)
    
    async def save_log(self, data: dict):
        """Save log entry to file and display."""
        level = data.get("level", "info").upper()
        message = data.get("message", "")
        source = data.get("source", "unknown")
        context = data.get("context", {})
        timestamp = data.get("timestamp", int(datetime.now().timestamp()))
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Color coding for terminal
        colors = {
            "DEBUG": "\033[36m",     # Cyan
            "INFO": "\033[32m",      # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "CRITICAL": "\033[35m"   # Magenta
        }
        reset = "\033[0m"
        color = colors.get(level, "")
        
        # Display to console
        print(f"\n{color}[{time_str}] [{source}] {level}{reset}")
        print(f"  {message}")
        if context:
            print(f"  Context: {json.dumps(context, indent=4)}")
        
        # Save to file (JSONL format)
        log_entry = {
            "timestamp": timestamp,
            "datetime": time_str,
            "level": level,
            "source": source,
            "message": message,
            "context": context
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Failed to save log: {e}")

def main():
    SERVER_URL = os.getenv("LOCOPYCAT_SERVER", "ws://localhost:8030/ws")
    LOG_FILE = os.getenv("LOG_FILE", "received_logs.jsonl")
    
    print("Starting Logs Client")
    print(f"Server: {SERVER_URL}")
    print(f"Log file: {LOG_FILE}")
    print("-" * 40)
    
    client = LogsClient(SERVER_URL, LOG_FILE)
    asyncio.run(client.run())

if __name__ == "__main__":
    main()
```

### Usage:

```bash
# Start log monitoring client
python clients/logs_client.py

# Send log entry
curl -X POST http://localhost:8030/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "level": "error",
    "message": "Payment processing failed",
    "source": "payment-service",
    "context": {
      "order_id": "ORD-12345",
      "amount": 99.99,
      "error_code": "CARD_DECLINED"
    }
  }'
```

---

## Example 3: Multi-Channel Client

A single client subscribed to multiple services.

### Client: `clients/multi_client.py`

```python
#!/usr/bin/env python3
"""Multi-channel client - handles clipboard, notifications, and logs."""

import asyncio
import sys
import os
import pyperclip

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients.base_client import BaseClient

class MultiClient(BaseClient):
    """Client subscribed to multiple channels."""
    
    def __init__(self, server_url: str):
        super().__init__(
            server_url=server_url,
            channels=["clipboard", "notify", "logs"],  # Multiple channels
            client_id="multi-client"
        )
    
    async def handle_message(self, message: dict):
        """Route messages based on channel."""
        channel = message.get("channel")
        
        handlers = {
            "clipboard": self.handle_clipboard,
            "notify": self.handle_notify,
            "logs": self.handle_logs
        }
        
        handler = handlers.get(channel)
        if handler:
            await handler(message)
        else:
            print(f"Unknown channel: {channel}")
    
    async def handle_clipboard(self, message: dict):
        """Handle clipboard messages."""
        action = message.get("action")
        data = message.get("data", {})
        
        if action == "copy":
            content = data.get("content", "")
            content_type = data.get("type", "text")
            
            if content_type == "text":
                pyperclip.copy(content)
                print(f"[CLIPBOARD] Copied: {content[:50]}...")
    
    async def handle_notify(self, message: dict):
        """Handle notification messages."""
        action = message.get("action")
        data = message.get("data", {})
        
        if action == "show":
            title = data.get("title", "")
            msg = data.get("message", "")
            print(f"[NOTIFY] {title}: {msg}")
    
    async def handle_logs(self, message: dict):
        """Handle log messages."""
        action = message.get("action")
        data = message.get("data", {})
        
        if action == "append":
            level = data.get("level", "INFO").upper()
            msg = data.get("message", "")
            source = data.get("source", "")
            print(f"[LOG:{level}] [{source}] {msg}")

def main():
    SERVER_URL = os.getenv("LOCOPYCAT_SERVER", "ws://localhost:8030/ws")
    
    print("Starting Multi-Channel Client")
    print(f"Server: {SERVER_URL}")
    print(f"Channels: clipboard, notify, logs")
    print("-" * 40)
    
    client = MultiClient(SERVER_URL)
    asyncio.run(client.run())

if __name__ == "__main__":
    main()
```

---

## Example 4: Command Execution Service

Execute commands on remote machines (use with caution!).

### Server: `app/routers/services/execute.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.connection_manager import manager
from typing import Optional
import time

router = APIRouter()

class CommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = 30  # seconds
    shell: Optional[bool] = False
    target_client_id: Optional[str] = None  # Optional: target specific client

@router.post("/api/execute")
async def execute_command(request: CommandRequest):
    """
    Send command to clients for execution.
    
    WARNING: This is powerful and potentially dangerous.
    Ensure proper security and authorization!
    
    Example:
        POST /api/execute
        {
            "command": "git pull && npm run build",
            "timeout": 60,
            "shell": true
        }
    """
    message = {
        "channel": "execute",
        "action": "run",
        "data": {
            "command": request.command,
            "timeout": request.timeout,
            "shell": request.shell,
            "target": request.target_client_id
        },
        "timestamp": int(time.time()),
        "message_id": f"cmd-{int(time.time() * 1000)}"
    }
    
    count = await manager.broadcast(message, channel="execute")
    
    return {
        "status": "dispatched",
        "clients_notified": count,
        "command": request.command,
        "message_id": message["message_id"]
    }
```

### Client: `clients/execute_client.py`

```python
#!/usr/bin/env python3
"""Command execution client - DANGEROUS, use with caution!"""

import asyncio
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients.base_client import BaseClient

class ExecuteClient(BaseClient):
    """Client that executes received commands."""
    
    def __init__(self, server_url: str, allowed_commands: list = None):
        super().__init__(
            server_url=server_url,
            channels=["execute"],
            client_id="execute-client"
        )
        # Whitelist of allowed commands (security!)
        self.allowed_commands = allowed_commands or []
    
    async def handle_message(self, message: dict):
        """Handle command execution messages."""
        if message.get("channel") != "execute":
            return
        
        action = message.get("action")
        data = message.get("data", {})
        
        if action == "run":
            await self.execute_command(data)
    
    async def execute_command(self, data: dict):
        """Execute a command with security checks."""
        command = data.get("command", "")
        timeout = data.get("timeout", 30)
        shell = data.get("shell", False)
        
        print(f"\n===== Command Execution =====")
        print(f"Command: {command}")
        print(f"Timeout: {timeout}s")
        
        # Security check: command whitelist
        if self.allowed_commands:
            if not any(command.startswith(allowed) for allowed in self.allowed_commands):
                print(f"❌ REJECTED: Command not in whitelist")
                print("=" * 40)
                return
        
        try:
            # Execute command
            result = subprocess.run(
                command if shell else command.split(),
                shell=shell,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            print(f"Exit code: {result.returncode}")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
            
        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT after {timeout}s")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("=" * 40)

def main():
    SERVER_URL = os.getenv("LOCOPYCAT_SERVER", "ws://localhost:8030/ws")
    
    # Define allowed commands for security
    ALLOWED_COMMANDS = [
        "git pull",
        "npm run build",
        "systemctl restart",
        "docker-compose up"
    ]
    
    print("Starting Execute Client")
    print(f"Server: {SERVER_URL}")
    print(f"Allowed commands: {', '.join(ALLOWED_COMMANDS)}")
    print("-" * 40)
    
    client = ExecuteClient(SERVER_URL, ALLOWED_COMMANDS)
    asyncio.run(client.run())

if __name__ == "__main__":
    main()
```

---

## Summary

These examples demonstrate:

1. **Notification Service**: User-facing alerts
2. **Logging Service**: Centralized monitoring
3. **Multi-Channel Client**: Handling multiple services
4. **Command Execution**: Remote control (with security considerations)

All services:
- Share the same security infrastructure
- Work independently without conflicts
- Can be combined in multi-channel clients
- Follow the same message protocol

Use these as templates for your custom services!
