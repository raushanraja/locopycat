import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables with defaults
AUTHORIZED_CLIENTS_FILE = os.getenv("AUTHORIZED_CLIENTS_FILE", "authorized_clients.txt")
SERVER_PRIVATE_KEY = os.getenv("SERVER_PRIVATE_KEY", "server_private.pem")
SERVER_PUBLIC_KEY = os.getenv("SERVER_PUBLIC_KEY", "server_public.pem")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))
