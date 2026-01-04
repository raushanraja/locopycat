# Quick Start Guide

## Understanding the Security Model

**TL;DR:** Only clients you explicitly authorize can receive clipboard data. Unauthorized connections are rejected immediately.

```bash
                          ┌──────────────┐
                          │   Server     │
                          │  locopycat   │
                          └──────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
            ┌─────────────┐          ┌─────────────┐
            │  Client A   │          │  Client B   │
            │  (authorized)│         │  (authorized)│
            └─────────────┘          └─────────────┘

                    │
                    ▼
            ┌─────────────┐
            │  Hacker     │
            │ (unauthorized)│
            └─────────────┘
                  ❌
         Rejected immediately
     NO keys exchanged, NO data sent
```

## Setup (5 minutes)

### 1. Install Dependencies
```bash
make setup
```

### 2. Start Server
```bash
make docker-detached
# or
make start-server
```

### 3. Authorize Your Client (First Time Only)
```bash
# On your local machine, this generates keys
python client.py
# Press Ctrl+C after seeing "Generating new client keys..."

# Copy public key to server (adjust path)
scp .keys/client_public.pem user@server:/path/to/locopycat/

# On server, authorize the client
python manage_clients.py add client_public.pem my-device

# Verify it's authorized
python manage_clients.py list
```

### 4. Start Client
```bash
# Now it can connect successfully!
python client.py
```

## Daily Usage

```bash
# Terminal 1: Server
make docker-detached

# Terminal 2, 3, 4...: Multiple clients
python client.py

# Send text (from anywhere)
curl -X POST http://localhost:8000/api/print \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello from all my devices!"}'
```

## Managing Clients

```bash
# List all authorized clients
python manage_clients.py list

# Add a new device
python manage_clients.py add /path/to/new-client/key.pem my-phone

# Remove compromised device
python manage_clients.py remove my-old-phone

# Export key for backup
python manage_clients.py export my-laptop backup/my-laptop.pem
```

## Quick Test

```bash
# 1. Start server
make docker-detached

# 2. Start client (you'll see "Generating new client keys..." then rejected)
python client.py

# 3. Note the fingerprint from server logs (e.g., abc123...)

# 4. Authorize using manage_clients.py
python manage_clients.py add .keys/client_public.pem my-test

# 5. Start client again (now it connects!)
python client.py

# 6. Send test data
curl -X POST http://localhost:8000/api/print \
  -H "Content-Type: application/json" \
  -d '{"content": "Security test successful!"}'
```

## Common Issues

### "Unauthorized client" Error
**Problem:** Client can't connect
**Solution:** Add the client to authorized list
```bash
python manage_clients.py add .keys/client_public.pem my-device
```

### Want to Add Another Device?
```bash
# Step 1: Generate keys on new device
python client.py  # Then Ctrl+C

# Step 2: Copy public key to server
scp .keys/client_public.pem server:/path/to/locopycat/

# Step 3: Authorize on server
python manage_clients.py add client_public.pem new-device-name
```

### Keys Generated Automatically?
Yes! Both server and client generate RSA-2048 keys on first run. No manual setup needed.

### What If Keys Are Stolen?
```bash
# Remove the compromised client immediately
python manage_clients.py remove compromised-device

# The thief's device will be rejected even if they have the keys
```

## Security Checklist

- ✅ Only authorized clients receive clipboard data
- ✅ Unauthorized connections rejected immediately
- ✅ All communication encrypted per-session
- ✅ Keys generated automatically (RSA-2048)
- ✅ Revocable (remove clients instantly)
- ✅ No plaintext transmission
- ✅ HMAC message integrity

## Configuration

Customize behavior using environment variables:

```bash
# Create configuration file
cp .env.example .env

# Edit settings
nano .env
```

See [CONFIG.md](CONFIG.md) for all configuration options.

## Need More Details?

- **Security Architecture:** See [SECURITY.md](SECURITY.md)
- **Complete README:** See [README.md](README.md)
