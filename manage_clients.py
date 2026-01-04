#!/usr/bin/env python3
"""
Manage authorized clients for locopycat server.
"""

import sys
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import hashlib

AUTHORIZED_CLIENTS_FILE = "authorized_clients.txt"
CLIENT_KEYS_DIR = ".keys"


def load_authorized_clients():
    """Load authorized client public keys from file."""
    authorized_keys = {}
    if os.path.exists(AUTHORIZED_CLIENTS_FILE):
        with open(AUTHORIZED_CLIENTS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        client_id, public_key_pem = parts
                        authorized_keys[client_id] = public_key_pem
    return authorized_keys


def save_authorized_clients(authorized_keys):
    """Save authorized client public keys to file."""
    with open(AUTHORIZED_CLIENTS_FILE, 'w') as f:
        for client_id, public_key_pem in authorized_keys.items():
            f.write(f"{client_id}:{public_key_pem}\n")


def get_key_fingerprint(public_key_pem):
    """Generate fingerprint from public key."""
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode(),
        backend=default_backend()
    )
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(public_key_bytes).hexdigest()[:16]


def add_client(public_key_file, client_name=None):
    """Add a client's public key to authorized list."""
    if not os.path.exists(public_key_file):
        print(f"Error: Public key file not found: {public_key_file}")
        return False
    
    # Read public key
    with open(public_key_file, 'r') as f:
        public_key_pem = f.read().strip()
    
    # Generate identifier
    fingerprint = get_key_fingerprint(public_key_pem)
    client_id = client_name if client_name else f"client_{fingerprint}"
    
    # Load existing authorized clients
    authorized = load_authorized_clients()
    
    # Check if already exists
    if client_id in authorized:
        print(f"Client '{client_id}' already exists in authorized list")
        response = input("Replace? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    # Add to authorized list
    authorized[client_id] = public_key_pem
    save_authorized_clients(authorized)
    
    print(f"Added client: {client_id}")
    print(f"Fingerprint: {fingerprint}")
    print(f"Total authorized clients: {len(authorized)}")
    return True


def remove_client(client_id):
    """Remove a client from the authorized list."""
    authorized = load_authorized_clients()
    
    if client_id not in authorized:
        print(f"Client '{client_id}' not found in authorized list")
        return False
    
    response = input(f"Remove client '{client_id}'? (y/N): ").strip().lower()
    if response != 'y':
        return False
    
    del authorized[client_id]
    save_authorized_clients(authorized)
    
    print(f"Removed client: {client_id}")
    print(f"Total authorized clients: {len(authorized)}")
    return True


def list_clients():
    """List all authorized clients."""
    authorized = load_authorized_clients()
    
    if not authorized:
        print("No authorized clients configured")
        return
    
    print(f"\nAuthorized Clients ({len(authorized)}):")
    print("-" * 60)
    for client_id, public_key_pem in authorized.items():
        fingerprint = get_key_fingerprint(public_key_pem)
        print(f"  ID: {client_id}")
        print(f"  Fingerprint: {fingerprint}")
        print()


def show_help():
    """Show help information."""
    print("""
Manage Authorized Clients for LoCopyCat

Usage:
  python manage_clients.py add <public_key_file> [client_name]
    Add a client's public key to the authorized list
    
  python manage_clients.py remove <client_id>
    Remove a client from the authorized list
    
  python manage_clients.py list
    List all authorized clients
  
  python manage_clients.py export <client_id> <output_file>
    Export a client's public key to a file for distribution

Examples:
  # Add a client (using client's public key file)
  python manage_clients.py add .keys/client_public.pem my-laptop
  
  # List all authorized clients
  python manage_clients.py list
  
  # Remove a client
  python manage_clients.py remove my-laptop
  
  # Export a client's public key
  python manage_clients.py export my-laptop my-laptop-key.pem
  
Note:
  - Client public keys are stored in authorized_clients.txt
  - Each client must be added to this list before connecting
  - Use this script on the server machine
    """)


def export_client(client_id, output_file):
    """Export a client's public key to a file."""
    authorized = load_authorized_clients()
    
    if client_id not in authorized:
        print(f"Client '{client_id}' not found in authorized list")
        return False
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(authorized[client_id])
    
    print(f"Exported client '{client_id}' public key to: {output_file}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "add":
        if len(sys.argv) < 3:
            print("Error: Missing public key file")
            print("Usage: python manage_clients.py add <public_key_file> [client_name]")
            sys.exit(1)
        public_key_file = sys.argv[2]
        client_name = sys.argv[3] if len(sys.argv) > 3 else None
        add_client(public_key_file, client_name)
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Error: Missing client ID")
            print("Usage: python manage_clients.py remove <client_id>")
            sys.exit(1)
        remove_client(sys.argv[2])
    
    elif command == "list":
        list_clients()
    
    elif command == "export":
        if len(sys.argv) < 4:
            print("Error: Missing arguments")
            print("Usage: python manage_clients.py export <client_id> <output_file>")
            sys.exit(1)
        export_client(sys.argv[2], sys.argv[3])
    
    elif command in ["help", "-h", "--help"]:
        show_help()
    
    else:
        print(f"Unknown command: {command}")
        show_help()
        sys.exit(1)
