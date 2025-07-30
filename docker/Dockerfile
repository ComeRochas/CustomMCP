FROM python:3.11-slim

WORKDIR /app

# Install uv for faster package management
RUN pip install uv

# Copy requirements file
COPY requirements.txt .

# Install dependencies using uv
RUN uv venv
RUN uv pip install -r requirements.txt

# Copy application code
COPY server.py .
COPY client.py .

# Expose the port the server runs on
EXPOSE 8050

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run.py .
COPY server.py .
COPY client.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 mcpuser
RUN chown -R mcpuser:mcpuser /app
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8050/health || exit 1

# Expose the port
EXPOSE 8050

# Run the server
CMD ["python", "run.py", "server"]
