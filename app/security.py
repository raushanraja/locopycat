import os
import base64
import hashlib
from typing import Dict, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from app.config import SERVER_PRIVATE_KEY, SERVER_PUBLIC_KEY, AUTHORIZED_CLIENTS_FILE

# Generate RSA key pair for server
def generate_server_keys():
    """Generate or load server RSA key pair."""
    private_key_path = SERVER_PRIVATE_KEY
    public_key_path = SERVER_PUBLIC_KEY
    
    # Check if keys already exist
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        print("Loading existing server keys...")
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        return private_key, public_key
    
    # Generate new keys
    print("Generating new server keys...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    
    # Save keys
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    
    print("Server keys generated and saved")
    return private_key, public_key

# Initialize server keys
server_private_key, server_public_key = generate_server_keys()

def load_authorized_clients() -> Dict[str, str]:
    """Load authorized client public keys from file.
    
    Returns dict mapping fingerprint to client_id.
    """
    authorized_keys = {}
    if os.path.exists(AUTHORIZED_CLIENTS_FILE):
        with open(AUTHORIZED_CLIENTS_FILE, 'r') as f:
            content = f.read().strip()
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Check if this is the new format (base64 with ::)
                if '::' in line:
                    parts = line.split('::', 1)
                    if len(parts) == 2:
                        client_id, encoded_key = parts
                        try:
                            public_key_pem = base64.b64decode(encoded_key).decode()
                            # Generate fingerprint from public key
                            public_key = serialization.load_pem_public_key(
                                public_key_pem.encode(),
                                backend=default_backend()
                            )
                            public_key_bytes = public_key.public_bytes(
                                encoding=serialization.Encoding.DER,
                                format=serialization.PublicFormat.SubjectPublicKeyInfo
                            )
                            fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[:16]
                            authorized_keys[fingerprint] = client_id
                        except Exception as e:
                            print(f"Warning: Failed to load key for {client_id}: {e}")
                # Old format (single line with :)
                elif ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        client_id, public_key_pem = parts
                        # Replace literal \n with actual newlines
                        public_key_pem = public_key_pem.replace('\\n', '\n')
                        try:
                            public_key = serialization.load_pem_public_key(
                                public_key_pem.encode(),
                                backend=default_backend()
                            )
                            public_key_bytes = public_key.public_bytes(
                                encoding=serialization.Encoding.DER,
                                format=serialization.PublicFormat.SubjectPublicKeyInfo
                            )
                            fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[:16]
                            authorized_keys[fingerprint] = client_id
                        except Exception as e:
                            print(f"Warning: Failed to load key for {client_id}: {e}")
    return authorized_keys


def check_client_authorized(public_key_pem: str) -> Tuple[bool, str]:
    """Check if a client's public key is authorized."""
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[:16]
        
        authorized = load_authorized_clients()
        if fingerprint in authorized:
            return True, authorized[fingerprint]
        
        return False, fingerprint
    except Exception as e:
        print(f"Error checking authorization: {e}")
        return False, "invalid"

def cycle_key(key: bytes, length: int) -> bytes:
    """Cycle the key to match required length."""
    return (key * ((length // len(key)) + 1))[:length]

# Load authorized clients on startup
authorized_clients = load_authorized_clients()
print(f"Loaded {len(authorized_clients)} authorized client(s)")
