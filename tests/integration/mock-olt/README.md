# Mock OLT SSH Server

A containerized SSH server that simulates a Cambium Fiber OLT device for testing purposes.

## Features

- ✅ **Realistic SSH server** - Accepts connections on port 22
- ✅ **Password authentication** - Username: `admin`, Password: `password`
- ✅ **Command processing** - Responds to `info` and `show all` commands
- ✅ **Realistic output** - Includes CLI prompts, ANSI codes, warnings
- ✅ **Fixture-based** - Returns real OLT data from fixture file
- ✅ **Multiple instances** - Can run multiple mock OLTs with different IPs/ports

## Quick Start

### Run with Docker

```bash
# Build the image
docker build -t mock-olt tests/integration/mock-olt/

# Run the container
docker run -d -p 2222:22 --name mock-olt-1 mock-olt

# Test connection
sshpass -p 'password' ssh -p 2222 admin@localhost
```

### Run with Docker Compose

```yaml
services:
  mock-olt-1:
    build: ./tests/integration/mock-olt
    ports:
      - "2222:22"
    volumes:
      - ./tests/fixtures:/app/fixtures:ro
```

### Run Standalone (for development)

```bash
# Install dependencies
pip install asyncssh

# Run the server
cd tests/integration/mock-olt
python3 mock_olt_ssh_server.py --port 2222
```

## Testing with the Python Script

```bash
# Test against mock OLT
./templates/zabbix/cambium-fiber/cambium_olt_ssh_json.py localhost:2222 password

# Should return the same JSON as the fixture
```

## Configuration

### Environment Variables

- `FIXTURE_PATH` - Path to JSON fixture file
- `SSH_PORT` - SSH port to listen on (default: 22)
- `ADMIN_PASSWORD` - Password for admin user (default: password)

### Command Line Options

```bash
python3 mock_olt_ssh_server.py --help

Options:
  --fixture PATH     Path to JSON fixture file
  --port PORT        SSH port to listen on (default: 22)
  --host HOST        Host to bind to (default: 0.0.0.0)
  --password PASS    Password for admin user (default: password)
```

## Creating Multiple Mock OLTs

For integration testing, you can run multiple mock OLTs:

```yaml
services:
  mock-olt-1:
    build: ./tests/integration/mock-olt
    ports:
      - "2222:22"
    environment:
      - OLT_NAME=OLT-Building-A

  mock-olt-2:
    build: ./tests/integration/mock-olt
    ports:
      - "2223:22"
    environment:
      - OLT_NAME=OLT-Building-B

  mock-olt-error:
    build: ./tests/integration/mock-olt
    ports:
      - "2224:22"
    command: ["python3", "/app/mock_olt_ssh_server.py", "--password", "WrongPassword"]
```

## Supported Commands

- `info` - Returns info command response
- `show all` - Returns full OLT JSON data
- `exit`, `quit`, `logout` - Closes connection

## Architecture

```
┌─────────────────┐
│  Zabbix Server  │
└────────┬────────┘
         │ SSH (sshpass)
         ▼
┌─────────────────┐
│   Mock OLT SSH  │
│     Server      │
├─────────────────┤
│  asyncssh       │  ← Python SSH server
│  Port 22        │
│  admin/password │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fixture JSON    │  ← Real OLT data
│ olt-sample-     │
│ output.json     │
└─────────────────┘
```

## Troubleshooting

### Connection refused
```bash
# Check if container is running
docker ps | grep mock-olt

# Check logs
docker logs mock-olt-1
```

### Authentication failed
```bash
# Verify password
docker exec mock-olt-1 env | grep PASSWORD

# Check server logs
docker logs mock-olt-1
```

### No JSON in output
```bash
# Check fixture file exists
docker exec mock-olt-1 ls -la /app/fixtures/

# Verify fixture is valid JSON
docker exec mock-olt-1 cat /app/fixtures/olt-sample-output.json | jq .
```

## Development

### Adding Error Scenarios

Edit `mock_olt_ssh_server.py` to add:

- **Timeout simulation** - Add `await asyncio.sleep(60)` before response
- **Malformed JSON** - Return `{"broken": json}`
- **Connection drops** - Call `self._chan.exit(1)` randomly
- **Slow responses** - Add delays with `asyncio.sleep()`

### Updating Fixture Data

```bash
# Capture fresh data from real OLT
./templates/zabbix/cambium-fiber/cambium_olt_ssh_json.py 192.168.50.10 password \
  > tests/fixtures/olt-sample-output.json

# Rebuild container
docker-compose build mock-olt-1
```
