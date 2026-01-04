# LoCopyCat - Client-Server Clipboard Service

A FastAPI server with WebSocket support that broadcasts received text to connected clients for clipboard operations.

## Architecture

```
┌─────────────┐         WebSocket          ┌─────────────┐
│   Server    │ ◄───────────────────────► │   Client    │
│ (in Docker) │                            │   (Local)   │
│   :8000     │                            │   clipboard │
└─────────────┘                            └─────────────┘
     ▲                                        ▲
     │                                        │
  HTTP/POST                            Local machine
/print, /api/print
```

## Setup

### Using Makefile (Recommended)

The project includes a Makefile for easy setup and running:

```bash
# Show all available commands
make help

# Setup virtual environment and install dependencies
make setup

# Run the client
make run-client

# Run the server locally (for development)
make run-server

# Run server in background
make start-server    # Start in background
make stop-server     # Stop background server
make restart-server  # Restart background server

# Docker commands
make docker-detached    # Start services in background (detached)
make docker-up         # Start services (foreground)
make docker-down       # Stop services
make docker-logs       # View container logs
make docker-restart    # Restart services
```

### Manual Setup

#### Server (Docker)

1. Build and run the server:
```bash
docker-compose up --build
# Or manually:
docker build -t locopycat .
docker run -p 8000:8000 locopycat
```

#### Client (Local Machine)

1. Install dependencies for the client:
```bash
pip install websockets pyperclip
```

2. Run the client:
```bash
python client.py
```

## Usage

### Send text via API
```bash
curl -X POST http://localhost:8000/api/print \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, clipboard!"}'
```

### Send text via HTML form
Visit `http://localhost:8000/` in your browser and paste text in the form.

### Test with WebSocket
```bash
# Using websocat or wscat
wscat -c ws://localhost:8000/ws
# You'll receive messages when text is sent to /print or /api/print
```

## Multiple Clients

You can run multiple clients simultaneously. All connected clients will receive and copy the text to their local clipboards.

```bash
# Terminal 1
python client.py

# Terminal 2
python client.py

# Terminal 3
python client.py
```

## Docker Configuration

The exposed port is 8000. Make sure your Docker setup allows external access:

- Update `SERVER_URL` in `client.py` to match your server address
- For remote servers, use the server's IP address instead of `localhost`
- Example: `SERVER_URL = "ws://192.168.1.100:8000/ws"`

## Requirements

### Server
- fastapi
- uvicorn
- websockets

### Client
- Python 3.7+
- websockets
- pyperclip
- On Linux: xclip or xsel (install via package manager)

Install xclip on Linux:
```bash
sudo apt-get install xclip  # Debian/Ubuntu
sudo dnf install xclip      # Fedora
sudo pacman -S xclip        # Arch Linux
```

## Example Workflow

### Using Docker (recommended)
1. Start the server in background: `make docker-detached`
2. Start a client(s): `make run-client`
3. Send text:
   ```bash
   curl -X POST http://localhost:8000/api/print \
     -H "Content-Type: application/json" \
     -d '{"content": "This text will be copied to all client clipboards!"}'
   ```
4. View logs if needed: `make docker-logs`
5. Stop server when done: `make docker-down`

### Using Background Server (local)
1. Start the server in background: `make start-server`
2. Start client(s): `make run-client`
3. When done, stop the server: `make stop-server`
4. Check logs: `cat server.log`
