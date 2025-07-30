# Docker Deployment Guide

This guide covers how to run CustomMCP using Docker.

## 🚀 Quick Start

### Build and Run Server

```bash
# Build the Docker image (from project root)
docker build -f docker/Dockerfile -t custom-mcp .

# Run the server container
docker run -p 8050:8050 custom-mcp

# Run with custom settings
docker run -p 8050:8050 -e HOST=0.0.0.0 -e DEBUG=true custom-mcp

# Run in background (detached mode)
docker run -d -p 8050:8050 --name custom-mcp-server custom-mcp
```

### Verify Server is Running

```bash
# Check if container is running
docker ps

# Test server health
curl http://localhost:8050/health

# View server logs
docker logs custom-mcp-server
```

### Running the Client

Once the server is running, you can run the client in several ways:

#### Option 1: Local Client (Recommended)

Run the client locally while server runs in Docker:

```bash
# Make sure you have the dependencies installed locally
pip install -r requirements.txt

# Run client pointing to Docker server
python run.py client
# or directly: python src/client.py
```

#### Option 2: Client in Docker Container

Run the client inside a Docker container:

```bash
# Run client in interactive mode
docker run -it --network="host" custom-mcp python run.py client

# Or connect to running server container
docker exec -it <server-container-name> python run.py client
```

#### Option 3: Separate Client Container

```bash
# Build client-specific image (if needed)
docker run -it --rm --network="host" \
  -e SERVER_URL=http://localhost:8050 \
  custom-mcp python run.py client
```

## Troubleshooting

If you encounter connection issues:

1. **Check if the server is running**: Make sure the Docker container is running with `docker ps`.

2. **Verify port mapping**: Ensure the port is correctly mapped with `docker ps` or by checking the output of the `docker run` command.

3. **Check server logs**: View the server logs with `docker logs <container_id>` to see if there are any errors.

4. **Host binding**: The server is configured to bind to `0.0.0.0` instead of `127.0.0.1` to make it accessible from outside the container. If you're still having issues, you might need to check your firewall settings.

5. **Network issues**: If you're running Docker on a remote machine, make sure the port is accessible from your client machine.

## Notes

- The server is configured to use SSE (Server-Sent Events) transport and listens on port 8050.
- The client connects to the server at `http://localhost:8050/sse`.
- Make sure the server is running before starting the client.

## 📊 Monitoring

### Basic Health Check

```bash
curl http://localhost:8050/health
```

### Container Stats

```bash
docker stats <container-name>
```
