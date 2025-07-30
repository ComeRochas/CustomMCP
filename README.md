# CustomMCP - Personal MCP Server Implementation

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

A personal implementation of a Model Control Protocol (MCP) server showcasing weather data integration, calculator tools, and multi-transport support. Built as a learning project to demonstrate MCP protocol understanding and modern Python development practices.

## 🚀 Features

- **Weather Integration**: Real-time weather forecasts and alerts via National Weather Service API
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
│       └── time_utils.py
└── docker/              # Docker configuration

```



### Available Tools

#### Weather Tools
- `get_forecast(latitude, longitude)` - Get 5-day weather forecast
- `get_alerts(state)` - Get active weather alerts for US states

#### Calculator Tools
- `add(a, b)` - Addition
- `subtract(a, b)` - Subtraction  
- `multiply(a, b)` - Multiplication
- `divide(a, b)` - Division
- `power(base, exponent)` - Exponentiation

#### Utility Tools
- `get_time()` - Current UTC time
- `get_timestamp()` - Unix timestamp

## ⚙️ Configuration

Environment variables:

```env
# Server settings
HOST=localhost
PORT=8050
TRANSPORT=sse

# Client settings (for the chatbot inside the client)
MODEL=qwen3:8b

# Optional settings
DEBUG=false
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30
```

## 🐳 Docker Deployment

See [Docker README](docker/README.md) for detailed Docker setup and deployment options.

## 🛠️ Development

### Prerequisites
- Python 3.11+
- pip or uv package manager
- Docker (optional)



## 📚 Technical Details

This project demonstrates:
- **MCP Protocol Implementation**: Proper tool registration and multi-transport support
- **Modern Python**: Type hints, async/await, structured configuration
- **API Integration**: External weather service integration with error handling
- **Containerization**: Production-ready Docker setup
- **Code Organization**: Modular architecture with separation of concerns

## 🎯 Project Goals

This is a personal learning project to:
- Understand the Model Control Protocol specification
- Practice modern Python development patterns
- Explore AI tool integration possibilities

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- Weather data from [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
- Inspired by the Dave Ebbelaar's template(https://github.com/daveebbelaar/ai-cookbook)