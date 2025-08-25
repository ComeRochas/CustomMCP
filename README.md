# CustomMCP - Personal MCP Server Implementation

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

A personal implementation of a MCP Client consisting in a chatbot powered by GPT-OSS and an MCP server showcasing web search, weather data integration, calculator tools, and multi-transport support. Built as a learning project to demonstrate MCP protocol understanding.

## 🚀 Features

- **Web Search Tools**: Search the web via keywords or search a specific url via DuckDuckGo API
- **Weather Integration**: Real-time weather forecasts and alerts via National Weather Service API (in the US only)
- **Calculator Tools**: Basic mathematical operations (add, subtract, multiply, divide, power)
- **Time Utilities**: Current time and timestamp functions
- **Multi-Transport Support**: SSE, streamable-http, and stdio protocols
- **Docker Ready**: Containerized deployment with environment configuration
- **Interactive Client**: Demonstration client with Ollama integration

## 🏗️ Project Structure

```
CustomMCP/
├── src/
│   ├── server.py        # Main MCP server
│   ├── client.py        # Demo client with Ollama
│   ├── config.py        # Configuration management
│   └── tools/           # Tool implementations
│       ├── calculator.py
│       ├── weather.py
│       ├── web_search.py
│       └── time_utils.py
└── docker/              # Docker configuration

```

## How to Use

1 - Set up your virtual environment and install the requirements :
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

2 - Define the model you are going to run and the transport mode in .env (for example, MODEL=qwen3:8b and TRANSPORT=sse)

3 - Run the client and the server, depending on your transport mode :

stdio -> uv run src/client.py src/server.py

sse -> in a terminal : uv run src/server.py
in another terminal : uv run src/client.py <url_to_the_server>/sse (e.g. http://localhost:8050/sse)

streamable-http -> in a terminal : uv run src/server.py
in another terminal : uv run src/client.py <url_to_the_server>/mcp (e.g. http://localhost:8050/mcp)

## Available Tools

#### Web Tools

- `duckduckgo_search(query, max_results)` - Search the web using DuckDuckGo
- `duckduckgo_search(url, max_length, mode)` - Fetch and extract text content from a URL

#### Weather Tools

- `get_forecast(latitude, longitude)` - Get 5-day weather forecast in the US
- `get_alerts(state)` - Get active weather alerts for US states

#### Calculator Tools

- `add(a, b)` - Addition
- `subtract(a, b)` - Subtraction
- `multiply(a, b)` - Multiplication

#### Utility Tools

- `get_time()` - Current UTC time

#### Location Tools

- `get_location()` - Get current location of the server
- `get_location_by_ip(ip_adress)` - Get location information for a specific IP address

## ⚙️ Configuration

Environment variables:

```env
# Server settings
HOST=localhost
PORT=8050
TRANSPORT=sse

# Client settings (for the chatbot inside the client)
MODEL=openai/gpt-oss-120b

# Optional settings
DEBUG=false
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30

# Optional settings
PRINT_ALL_MODEL_OUTPUT=True # Print all model output to console (useful for debugging)
GPT_OSS_REASONING=medium

GROQ_API_KEY=YOUR_GROQ_API_KEY
```

## 🐳 Docker Deployment

See [Docker README](docker/README.md) for detailed Docker setup and deployment options.

## 🛠️ Development

### Prerequisites

- Python 3.11+
- pip or uv package manager
- Docker (optional)

## 🎯 Project Goals

This is a personal learning project to:

- Understand the Model Control Protocol specification
- Practice modern Python development patterns
- Explore AI tool integration possibilities

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- Inspired by Dave Ebbelaar's template(https://github.com/daveebbelaar/ai-cookbook)
