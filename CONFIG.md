# Configuration Guide

## Environment Variables

LoCopyCat supports configuration via environment variables. Create a `.env` file in the project root or set these variables in your environment.

### Quick Start

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to customize your settings:
   ```bash
   nano .env
   ```

3. Restart the server to apply changes

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTHORIZED_CLIENTS_FILE` | `authorized_clients.txt` | Path to file containing authorized client public keys |
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `CONNECTION_TIMEOUT` | `30` | Connection timeout in seconds |
| `SERVER_PRIVATE_KEY` | `server_private.pem` | Path to server private key |
| `SERVER_PUBLIC_KEY` | `server_public.pem` | Path to server public key |

### Example Configuration

```bash
# Server listening configuration
HOST=0.0.0.0
PORT=8000

# Authorization settings
AUTHORIZED_CLIENTS_FILE=/etc/locopycat/authorized_clients.txt

# Server key files
SERVER_PRIVATE_KEY=/etc/locopycat/keys/server_private.pem
SERVER_PUBLIC_KEY=/etc/locopycat/keys/server_public.pem

# Logging
LOG_LEVEL=INFO

# Connection settings
CONNECTION_TIMEOUT=30
```

## Usage with Different Run Methods

### Using Makefile

```bash
# Makefile automatically loads .env
make start-server
make run-server
```

### Using Docker

Create a `.env` file and pass it to docker-compose:

`docker-compose.yml`:
```yaml
services:
  locopycat:
    build: .
    container_name: locopycat
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

Or set environment variables directly:

```yaml
services:
  locopycat:
    build: .
    environment:
      - PORT=9000
      - LOG_LEVEL=DEBUG
```

### Using uvicorn directly

```bash
# uvicorn will load .env automatically
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Using systemd

Create `/etc/systemd/system/locopycat.service`:

```ini
[Unit]
Description=LoCopyCat Clipboard Server
After=network.target

[Service]
Type=simple
User=locopycat
WorkingDirectory=/opt/locopycat
Environment="PORT=8000"
Environment="LOG_LEVEL=INFO"
Environment="AUTHORIZED_CLIENTS_FILE=/etc/locopycat/authorized_clients.txt"
ExecStart=/opt/locopycat/.venv/bin/uvicorn main:app --host 0.0.0.0 --port ${PORT}
Restart=always

[Install]
WantedBy=multi-user.target
```

## Advanced Configuration

### Custom Authorization File

Store authorized clients in a different location:

```bash
# .env
AUTHORIZED_CLIENTS_FILE=/path/to/secure/location/authorized_clients.txt
```

### Multiple Deployment Environments

Create different `.env` files for different environments:

```bash
# Development
cp .env.example .env.development
# Edit .env.development

# Production
cp .env.example .env.production
# Edit .env.production

# Load specific environment
export $(cat .env.production | xargs)
make start-server
```

### Security Hardening

For production deployments:

```bash
# Restrict server to localhost behind reverse proxy
HOST=127.0.0.1

# Use non-standard port
PORT=9443

# Store keys in secure directory
SERVER_PRIVATE_KEY=/etc/locopycat/secure/private.pem
SERVER_PUBLIC_KEY=/etc/locopycat/secure/public.pem
AUTHORIZED_CLIENTS_FILE=/etc/locopycat/secure/authorized_clients.txt
```

## Environment-Specific Settings

### Development

```bash
# .env
LOG_LEVEL=DEBUG
HOST=localhost
PORT=8000
```

### Production

```bash
# .env.production
LOG_LEVEL=WARNING
HOST=0.0.0.0
PORT=8000
CONNECTION_TIMEOUT=60
```

### Testing

```bash
# .env.test
LOG_LEVEL=ERROR
HOST=localhost
PORT=8001
AUTHORIZED_CLIENTS_FILE=test_authorized_clients.txt
```

## Troubleshooting

### Environment Variables Not Loading

1. Ensure `.env` file exists in the project root
2. Check file permissions: `ls -la .env`
3. Verify python-dotenv is installed: `ls .venv/lib/*/site-packages/dotenv`
4. Check that variables are not commented out (remove `#` prefix)

### Configuration Priority

Environment variables are loaded in this order (later overrides earlier):

1. Default values in code (`os.getenv("VAR", "default")`)
2. `.env` file in project root
3. System environment variables
4. Docker/Kubernetes environment variables

### Validating Configuration

Test your configuration before starting:

```python
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    "AUTHORIZED_CLIENTS_FILE",
    "HOST", 
    "PORT"
]

missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"Missing variables: {missing}")
else:
    print("All required variables set")
```

## Best Practices

1. **Never commit `.env`** - It's already in `.gitignore`
2. **Use version control for `.env.example`** - Document all possible variables
3. **Separate configs per environment** - `.env.development`, `.env.production`
4. **Document custom values** - Add comments in `.env.example`
5. **Rotate sensitive values** - Especially for keys and passwords
6. **Restrict file permissions** - `chmod 600 .env` for production
7. **Use secrets management** - For production, consider tools like:
   - HashiCorp Vault
   - AWS Secrets Manager
   - Kubernetes Secrets
   - Docker Secrets
