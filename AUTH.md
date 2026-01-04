# Authentication & Authorization Documentation

## Overview

LoCopyCat uses a two-tier security model:

1. **Authorization** - Only pre-registered clients can connect
2. **Authentication** - RSA public/private key exchange for encrypted communication

This ensures that:
- Only authorized devices receive clipboard content
- All communication is encrypted with per-session keys
- Unauthorized connections are rejected immediately

## Authorization vs Authentication

### Authorization (Access Control)
- **Before** connection - Server checks if client is in `authorized_clients.txt`
- Uses **client public key fingerprint** for identification
- Rejects unauthorized clients without any key exchange

### Authentication (Secure Communication)
- **After** authorization - Both parties perform cryptographic handshake
- Exchanges encrypted session secrets
- Derives shared secret for message encryption

## Key Exchange & Authorization Flow

```
Client                                    Server
  |                                         |
  |--- (1) Send public key ---------------->|
  |                                         |
  |       Check if authorized (fingerprint) |
  |                                         |
  |<-- (2) Auth success / Rejection -------|
  |                                         |
  |        (Continue if authorized)        |
  |                                         |
  |<-- (3) Send server public key ---------|
  |                                         |
  |<-- (4) Send encrypted server secret ---|
  |                                         |
  |--- (5) Send encrypted client secret --->|
  |                                         |
  |<-- (5) Authentication confirmation ----|
  |                                         |
```

**Step Details:**

1. **Authorization Check**: Server calculates client's public key fingerprint and checks against `authorized_clients.txt`
2. **If unauthorized**: Server immediately closes connection (code 4003) without any data exchange
3. **If authorized**: Continue with normal authentication flow
4. **Key exchange**: Both parties exchange public keys and encrypted secrets
5. **Shared secret**: Derive using SHA256: `SHA256(server_secret + client_secret)`

## Managing Authorized Clients

### Adding a New Client

1. Start the client (generates keys):
   ```bash
   python client.py
   # Stop it with Ctrl+C after keys are generated
   ```

2. Export client's public key to server:
   ```bash
   # On client machine
   scp .keys/client_public.pem server:/path/to/locopycat/
   ```

3. On server, authorize the client:
   ```bash
   python manage_clients.py add client_public.pem my-laptop
   ```

4. Restart the client - it can now connect

### Using manage_clients.py

```bash
# List all authorized clients
python manage_clients.py list

# Add a client with custom name
python manage_clients.py add .keys/client_public.pem "My MacBook"

# Remove a client
python manage_clients.py remove my-laptop

# Export a client's key for backup/sharing
python manage_clients.py export my-laptop backup/my-laptop-key.pem
```

### authorized_clients.txt Format

```text
# Comments start with #
client_id:-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----
client_id2:-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----
```

## Encryption

### Payload Format

Messages are encrypted and sent with the following format:
```json
{
  "iv": "<base64-encoded initialization vector>",
  "hmac": "<base64-encoded HMAC signature>",
  "data": "<base64-encoded encrypted data>"
}
```

### Encryption Method

Currently uses XOR encryption with HMAC for integrity verification. For production use, consider replacing with AES-GCM.

**Note:** The current implementation uses simplified XOR encryption with cycling keys. In production environments, replace with industry-standard encryption like AES-GCM.

## Security Considerations

### Current Implementation (Development)

**Authorization Layer (Access Control):**
- **Whitelist-based**: Only pre-registered clients can connect
- **Public key fingerprinting**: Each client identified by SHA256 hash of public key
- **Immediate rejection**: Unauthorized clients rejected before any encryption setup
- **No handshake**: No key exchange for unauthorized connections

**Authentication Layer (Encryption):**
- **RSA-2048**: Provides strong asymmetric encryption
- **Unique session secrets**: Each connection uses freshly generated secrets
- **HMAC verification**: Ensures message integrity
- **No key reuse**: New secrets for each connection

**Security Benefits:**
1. **Zero unauthorized access**: Unregistered clients cannot connect, even with correct keys
2. **Encrypted communication**: All clipboard content encrypted per-session
3. **No data leakage**: Server never sends data to unauthorized connections
4. **Device-specific**: Each client must be individually authorized
5. **Revocable**: Clients can be removed instantly by deleting from authorized list

### Why Authorization + Authentication?

**Authorization prevents:**
- Anyone from connecting to your clipboard server
- Network scanners from exploiting the service
- Malicious clients from receiving encrypted data

**Authentication ensures:**
- Only the intended client receives data (even if keys are stolen)
- Communications are encrypted end-to-end
- Message integrity via HMAC verification

Together, they provide defense-in-depth security.

### Recommendations for Production

1. **Use AES-GCM**: Replace XOR encryption with proper AES-256-GCM
2. **Add key rotation**: Implement periodic key rotation for server keys
3. **Rate limiting**: Implement connection rate limiting to prevent brute force
4. **Token expiration**: Add session timeout mechanisms
5. **Add TLS**: Use HTTPS/WSS for additional transport layer security
6. **Audit logging**: Log all connection attempts (successful and failed)
7. **Backup authorized list**: Keep backups of `authorized_clients.txt`
8. **Restrict file permissions**: Ensure `authorized_clients.txt` is 600

## Key Storage

### Server Keys

- **Location**: `server_private.pem`, `server_public.pem`
- **Permissions**: Should be restricted to owner (600 on Unix)
- **Backup**: Keep backups of private key securely

### Client Keys

- **Location**: `.keys/client_private.pem`, `.keys/client_public.pem`
- **Permissions**: Should be restricted to owner (600 on Unix)
- **Distribution**: Public key can be shared, private key must remain secret

## Usage

### Automatic Generation

Keys are automatically generated on first run. No manual setup required.

### Regenerating Keys

**Server:**
```bash
rm server_private.pem server_public.pem
# Keys will regenerate on next start
```

**Client:**
```bash
rm -rf .keys/
# Keys will regenerate on next start
```

### Using Existing Keys

Copy your existing keys to the respective directories before starting the server/client.

## Testing

### Test Connection

1. Start the server:
   ```bash
   make docker-detached
   # or
   make start-server
   ```

2. Start a client:
   ```bash
   make run-client
   ```

3. Check logs for authentication success:
   ```
   Initiating authentication...
   Authenticated as client_abc123
   Connected! Listening for clipboard updates...
   ```

## Troubleshooting

### Authentication Fails

1. **Check key permissions**:
   ```bash
   ls -la *.pem  # Server
   ls -la .keys/*.pem  # Client
   ```

2. **Regenerate keys**:
   ```bash
   # Server
   rm server_private.pem server_public.pem
   
   # Client
   rm -rf .keys/
   ```

3. **Verify cryptography libraries**:
   ```bash
   pip install cryptography>=41.0.0
   ```

### Connection Refused

- Ensure the server is running
- Check if port 8000 is available
- Verify `SERVER_URL` in `client.py` matches server address

## API Endpoints

### GET `/server-public-key`

Get the server's public key without WebSocket connection.

**Response:**
```json
{
  "public_key": "-----BEGIN PUBLIC KEY-----\n..."
}
```

## Security Best Practices

1. **Never commit keys to version control** (.gitignore includes *.pem)
2. **Restrict file permissions** (chmod 600 for private keys)
3. **Use strong passwords** if adding encryption-at-rest
4. **Monitor for unauthorized access**
5. **Update cryptography libraries regularly**
6. **Use TLS in production** for additional transport security
