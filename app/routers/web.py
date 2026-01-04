from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.connection_manager import manager

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
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

@router.post("/print")
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
