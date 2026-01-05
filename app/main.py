from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import web, api, websocket
import uvicorn

app = FastAPI()

# Include routers
app.include_router(web.router)
app.include_router(api.router)
app.include_router(websocket.router)

# If you have static files, you can mount them here
# app.mount("/static", StaticFiles(directory="static"), name="static")

# if __name__ == "__main__":
#     # This allows running the server directly with python -m app.main
#     # Increased WebSocket max size to 50MB for large images
#     uvicorn.run(
#         "app.main:app", 
#         host="0.0.0.0", 
#         port=8000, 
#         reload=True,
#         ws_max_size=52428800  # 50MB
#     )
