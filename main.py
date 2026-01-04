from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
import json

app = FastAPI()

# Track active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)

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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        manager.disconnect(websocket)
        print(f"Client connection error: {e}")


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
