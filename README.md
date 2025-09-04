# CustomMCP - Personal MCP Server Implementation

A personal implementation of a MCP Client consisting in a chatbot powered by GPT-OSS and an MCP server showcasing web search, location tools, calculator tools.


## 🏗️ Project Structure

```
CustomMCP/
├── src/
│   ├── server.py        # Main MCP server
│   ├── client.py        # Chatbot powered by Groq
│   ├── config.py        # Configuration management
│   └── tools/           # Tool implementations
│       ├── calculator.py
│       ├── location.py
│       ├── web_search.py
│       └── time_utils.py
├── requirements.txt
└── README.md

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


## Client 

The client side is entirely defined in 'src/client.py' and interacts with the server via Model Context Protocol, which is defined in mcp library. It is a chatbot powered by Groq (a tool which enables you to call LLMs and runs calculation on external hardware).

The chatbot is defined with the following logic :
- A loop is instantiated, where the model expects a query from the user
- The model reasons and determines whether it needs to call tools to answer the query. 
- If no tools are needed, it directly answers.
- If tools are needed, tools will be successfuly called (requesting approval from the user before every tool call).
- After all tools were called (or when the model was called too many times in a row, to prevent excessive token use), an answer is produced.
-> The loop restarts, and the model does not remember the conversation history.

This logic is divided in different functions for the code to be more readable. Model's reasoning is shown to the user via streaming (tokens are printed as they are being processed). When parameter 'print_all_output=False' in '.env', only the model's very last answer (after tool calls) is printed.

## Server

In order to add tools, you can :
- Create a new toolclass.py in src/tools/
- Define your ToolClass in toolclass.py in which you create the functions you wish to add
- Add your ToolClass to src/tools/__init__.py
- Add your defined tools to src/client.py, declaring them with @server.tool()

These are the exact files you have to create/modify in order to add/remove tools. You can simply copy the syntax from the tools already created.

#### Web Tools

- `brave_search(keywords, max_results, country[Opt])` - Search the web using DuckDuckGo
- `fetch_url_content(url, max_length, mode)` - Fetch and extract text content from a URL


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
BRAVE_API_KEY=YOUR_BRAVE_API_KEY
```


## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- Inspired by Dave Ebbelaar's template(https://github.com/daveebbelaar/ai-cookbook)
