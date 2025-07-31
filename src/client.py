import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

import time
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # Configure Ollama client
        self.ollama_client = AsyncOpenAI(
            base_url="http://localhost:11434/v1",  # Ollama API endpoint
            api_key="ollama"  # Ollama doesn't need a real API key
        )

    async def connect_to_server(self, server_path_or_url: str):
        """Connect to an MCP server via STDIO or SSE based on TRANSPORT env variable
        
        Args:
            server_path_or_url: Path to server script for STDIO or URL for SSE
        """
        transport = os.getenv("TRANSPORT", "stdio").lower()
        
        if transport == "sse":
            # Connect via SSE
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(server_path_or_url)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(sse_transport[0], sse_transport[1])
            )
        
        elif transport == 'streamable-http':
            http_transport = await self.exit_stack.enter_async_context(
                streamablehttp_client(server_path_or_url)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(http_transport[0], http_transport[1])
            )
        
        elif transport == "stdio":
            # Connect via STDIO (code existant)
            is_python = server_path_or_url.endswith('.py')
            is_js = server_path_or_url.endswith('.js')
            if not (is_python or is_js):
                raise ValueError("For STDIO transport, server must be a .py or .js file")
                
            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command,
                args=[server_path_or_url],
                env=None
            )
            
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            
        else:
            raise ValueError(f"Unsupported transport: {transport}. Use 'stdio' or 'sse'")
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("Model :", os.getenv("MODEL", "llama3.1:8b"))
        print(f"Connected via {transport} to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str, model: str) -> str:
        """Process a query using Ollama and available tools"""
        messages = [
            {
            "role": "system",
            "content": "You are a helpful assistant. Respond naturally to user queries. You may call a tool if it permits to answer the question. When absolutely no tools corresponds or you lack an argument, you are encouraged to take an initiative and infere the missing argument or the response based on your knowledge and be honest about the initiative you took."
            },
            {
            "role": "user",
            "content": query
            }
        ]

        tools_list = await self.session.list_tools()
        available_tools = [{ 
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in tools_list.tools]

        # Initial Ollama API call
        response = await self.ollama_client.chat.completions.create(
            model=model,
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
            tool_choice="auto"
        )

        # Process response and handle tool calls
        final_text = []

        message = response.choices[0].message

        # For debugging
        if message.content and os.getenv("PRINT_ALL_MODEL_OUTPUT", "false").lower() == "true":
            final_text.append("First answer from the model: " + message.content)

        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    # Parse JSON string to dict more safely
                    import json
                    tool_args = json.loads(tool_call.function.arguments)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Warning: Failed to parse tool arguments: {e}")
                    tool_args = {}

                # Execute tool call
                try:
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_result = result.content[0].text if hasattr(result, 'content') else str(result)
                    
                    # For debugging
                    if os.getenv("PRINT_ALL_MODEL_OUTPUT", "false").lower() == "true":
                        final_text.append(f"Tool call : {tool_name} was called, with result: {tool_result}...")

                    # Simplified conversation format for better understanding
                    messages.append({
                        "role": "tool",
                        "content": f"Tool call : {tool_name} was called, with result: {tool_result}..."
                    })

                    # Get next response from Ollama
                    follow_up_response = await self.ollama_client.chat.completions.create(
                        model=model, 
                        max_tokens=1000,
                        messages=messages,
                    )

                    final_text.append("Response: " + follow_up_response.choices[0].message.content)

                except Exception as e:
                    final_text.append(f"[Error executing tool {tool_name}: {str(e)}]")
                    print(f"Tool execution error: {e}")

        else:
            # If no tool calls, just return the initial response
            final_text.append("Response: " + message.content)
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                start = time.time()
                
                if query.lower() == 'quit':
                    break

                model = os.getenv("MODEL", "llama3.1:8b")
                response = await self.process_query(query, model)
                print("\n" + response)
                print(f"Response time: {time.time() - start:.2f} seconds")
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    transport = os.getenv("TRANSPORT", "stdio").lower()
    
    if transport == "sse":
        # For SSE, expect URL as argument
        if len(sys.argv) < 2:
            print("Usage for SSE: python src/client.py <server_url>")
            print("Example: python src/client.py http://localhost:8050/sse")
            sys.exit(1)
    elif transport == "streamable-http":
        # For streamable-http, expect URL as argument
        if len(sys.argv) < 2:
            print("Usage for streamable-http: python src/client.py <server_url>")
            print("Example: python src/client.py http://localhost:8050/mcp")
            sys.exit(1)
    else:
        # For STDIO, expect script path as argument  
        if len(sys.argv) < 2:
            print("Usage for STDIO: python src/client.py <path_to_server_script>")
            print("Example: python src/client.py src/server.py")
            sys.exit(1)
            
    server_path_or_url = sys.argv[1]
    client = MCPClient()
    try:
        await client.connect_to_server(server_path_or_url)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())