# Security Architecture

## The Security Problem Solved

**Question:** "How does this make it secure? Anyone can just connect and exchange to get the text."

**Answer:** **Authorization** prevents unauthorized connections. Only pre-registered clients can receive data.

## Two-Layer Security Model

### Layer 1: Authorization (Access Control)
```
Unknown client → Connect Request
                    ↓
         Server checks authorized_clients.txt
                    ↓
           ┌────────┴────────┐
           ↓                 ↓
      Unauthorized      Authorized
           ↓                 ↓
      IMMEDIATE       Continue to
      REJECTION        Authentication
           ↓
   Connection closed
   No data exchanged
   No keys exchanged
```

### Layer 2: Authentication (Encryption)
```
Authorized client → Key exchange
                     ↓
            Shared secret derived
                     ↓
         All messages encrypted
                     ↓
       Data only sent to
    authorized clients
```

## Why Authorization Makes It Secure

### Without Authorization (Insecure)
```
Attacker → Connects → Gets encrypted messages
                          ↓
                  Can decrypt (if they have the right key)
                          ↓
                ❌ Clipboard data leaked
```

### With Authorization (Secure)
```
Attacker → Connects → Server checks whitelist
                               ↓
                         Client not in list
                               ↓
                    Connection immediately closed
                               ↓
                    ✅ No data exchanged
                    ✅ No encryption keys shared
                    ✅ Zero information given
```

## Key Difference

| Aspect | Encrypted-Only (Insecure) | Authenticated (Secure) |
|--------|---------------------------|------------------------|
| Can anyone connect? | Yes | Only authorized clients |
| Server sends data to? | All connected clients | Only registered clients |
| Attack vectors | Network sniffing, key theft | Only physical key theft |
| Revocable | No | Yes (remove from list) |
| Security model | Trust anyone who connects | Trust no one by default |

## Real-World Analogy

**Insecure (Encryption only):**
> House with a lock. If someone finds the key, they can enter and take everything.

**Secure (Authorization + Encryption):**
> House with a lock + a guest list. Security guard checks ID at the door - if not on list, they can't even try the door. Only invited guests get a key.

## Protection Against Attacks

### 1. Network Scanning
```bash
$ nmap -p 8000 localhost
PORT     STATE SERVICE
8000/tcp open  http-proxy

# Attacker can port scan, but...
# - They can't enumerate connected clients
# - They can't receive any data
# - Connection is rejected at auth layer
```

### 2. Connection Attempts
```python
# Attacker's client
try:
    await websocket.connect("ws://localhost:8000/ws")
    # Server immediately rejects:
    # WebSocketException: Connection closed (4003): Unauthorized client
except WebSocketException:
    print("Blocked! No way to get clipboard data")
```

### 3. Man-in-the-Middle
```
Attacker intercepts traffic:

Server ←──────→ Attacker ←──────→ Client
         (encrypted)     (blocked)

Result: Attacker can see encrypted packets, but:
- Cannot connect as a client (not authorized)
- Cannot decrypt captured packets (no shared secret)
- Cannot replay attacks (per-session secrets)
```

4. Key Theft
```
If client private key is stolen:

Attacker's key on stolen device
              ↓
       Connects to server
              ↓
   Server checks authorized list
              ↓
   Device not authorized (new fingerprint)
              ↓
        Connection rejected ✅

Solution: Remove old client from authorized list
```

## Authorization Workflow

### First-Time Setup
```bash
# 1. Start client (generates keys)
python client.py
# Keys created: .keys/client_public.pem, .keys/client_private.pem

# 2. Admin copies client public key to server
scp .keys/client_public.pem server:/path/to/locopycat/

# 3. Admin authorizes the client on server
python manage_clients.py add client_public.pem my-work-laptop

# 4. Server now accepts connections from this client
```

### Admin Controls
```bash
# See all authorized clients
python manage_clients.py list

# Remove a compromised device
python manage_clients.py remove my-old-phone

# Add a new device
python manage_clients.py add new-device-key.pem my-tablet
```

## Security Properties

### Confidentiality ✅
- Data only sent to authorized clients
- Encrypted with per-session keys
- Unauthorized clients receive nothing

### Integrity ✅
- HMAC verification on all messages
- Tampering detected and rejected

### Availability ✅
- Server remains available
- Attackers can't deny access by flooding (rejected immediately)

### Revocability ✅
- Clients can be removed instantly
- No key rotation needed

## Configuration

### Server: `authorized_clients.txt`
```text
# Only these clients can connect
laptop-home:-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----

work-desktop:-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----
```

### Client: `.keys/client_public.pem`
```text
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----
```

## Summary

**Is it secure?** **YES**, because:

1. ❌ **Unauthorized clients cannot connect** - Rejected immediately
2. ❌ **No data sent to unauthorized parties** - Zilch, zero, nada
3. ❌ **No keys exchanged with unauthorized clients** - No opportunity for attack
4. ✅ **Only pre-registered clients receive data** - Explicit authorization
5. ✅ **All communication encrypted** - End-to-end encryption per session
6. ✅ **Revocable** - Remove clients instantly without changing server keys

The combination of **authorization + authentication** ensures that only your specific devices can receive clipboard data, even if someone knows your server address or tries to intercept traffic.
