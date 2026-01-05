from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from app.connection_manager import manager
import base64

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Paste & Print</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .drop-zone { border: 3px dashed #ccc; padding: 30px; text-align: center; margin: 20px 0; border-radius: 10px; }
            .drop-zone.dragover { border-color: #4CAF50; background: #f0f0f0; }
            textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-family: monospace; }
            button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #45a049; }
            #preview { max-width: 100%; margin-top: 20px; border: 1px solid #ccc; border-radius: 5px; display: none; }
            #tabs { display: flex; gap: 10px; margin-bottom: 20px; }
            .tab { padding: 10px 20px; background: #f0f0f0; border-radius: 5px; cursor: pointer; }
            .tab.active { background: #4CAF50; color: white; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
        </style>
    </head>
    <body>
        <h2>Paste & Print</h2>
        
        <div id="tabs">
            <div class="tab active" onclick="switchTab('text')">Text</div>
            <div class="tab" onclick="switchTab('image')">Image</div>
        </div>
        
        <div id="text-tab" class="tab-content active">
            <form method="post" action="/print">
                <textarea name="content" rows="10" placeholder="Paste your text here..."></textarea><br><br>
                <button type="submit">Send Text to Clipboard</button>
            </form>
        </div>
        
        <div id="image-tab" class="tab-content">
            <form id="imageForm">
                <div class="drop-zone" id="dropZone">
                    <p>Drag & drop an image here or</p>
                    <input type="file" name="file" id="fileInput" accept="image/*" onchange="previewImage()">
                </div>
                <img id="preview" alt="Image preview">
                <br><br>
                <button type="button" onclick="sendImage()">Send Image to Clipboard</button>
            </form>
        </div>
        
        <script>
            function switchTab(tab) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById(tab + '-tab').classList.add('active');
            }
            
            function previewImage() {
                const file = document.getElementById('fileInput').files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        document.getElementById('preview').src = e.target.result;
                        document.getElementById('preview').style.display = 'block';
                    }
                    reader.readAsDataURL(file);
                }
            }
            
            const dropZone = document.getElementById('dropZone');
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });
            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('dragover');
            });
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                const file = e.dataTransfer.files[0];
                if (file && file.type.startsWith('image/')) {
                    document.getElementById('fileInput').files = e.dataTransfer.files;
                    previewImage();
                }
            });
            
            async function sendImage() {
                const file = document.getElementById('fileInput').files[0];
                if (!file) {
                    alert('Please select an image first');
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = async function(e) {
                    const base64Data = e.target.result.split(',')[1];
                    const mimeType = file.type;
                    
                    try {
                        const response = await fetch('/api/print', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                action: 'copy',
                                content: base64Data,
                                type: 'image',
                                mime_type: mimeType
                            })
                        });
                        const result = await response.json();
                        alert(`Image sent to ${result.broadcasted} client(s)!`);
                    } catch (error) {
                        alert('Failed to send image: ' + error);
                    }
                };
                reader.readAsDataURL(file);
            }
        </script>
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
        await manager.broadcast({"action": "copy", "content": content, "type": "text"})
        print(f"Content broadcasted to {len(manager.active_connections)} client(s)")
    
    return {"status": "printed", "broadcasted": len(manager.active_connections)}

@router.post("/print/image")
async def print_image(file: UploadFile = File(...)):
    """Handle image upload via multipart form."""
    print("===== Received Image (HTML Form) =====")
    print(f"Filename: {file.filename}")
    print(f"Content-Type: {file.content_type}")
    
    # Read image data
    image_data = await file.read()
    print(f"Size: {len(image_data)} bytes")
    print("=====================================")
    
    # Convert to base64 and broadcast
    base64_data = base64.b64encode(image_data).decode()
    await manager.broadcast({
        "action": "copy",
        "content": base64_data,
        "type": "image",
        "mime_type": file.content_type
    })
    
    print(f"Image broadcasted to {len(manager.active_connections)} client(s)")
    return {"status": "printed", "broadcasted": len(manager.active_connections)}

