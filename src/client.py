import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

import time
from openai import AsyncOpenAI
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def is_gpt_oss(model: str) -> bool:
    return isinstance(model, str) and model.startswith("openai/gpt-oss")

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Respond naturally to user queries. You may call a tool if it permits to answer the question. When absolutely no tools corresponds or you lack an argument, you are encouraged to take an initiative and infere the missing argument or the response based on your knowledge and be honest about the initiative you took."
            }
        ]
        # Add a small Harmony nudge only when using GPT-OSS
        model = os.getenv("MODEL", "llama3.1:8b")
        if is_gpt_oss(model):
            self.messages.append({
                "role": "system",
                "content": "Think privately if needed. Then ALWAYS provide a clear final answer in the assistant message body."
            })

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

    async def process_and_print(self, model: str, messages: list, available_tools: list, print_all_output: bool):
        # Prepare common kwargs; add Harmony options if GPT-OSS
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=1.1,
            max_tokens=1000,
            stream=True
        )
        if available_tools is not None:
            kwargs["tools"] = available_tools

        if is_gpt_oss(model):
            kwargs["reasoning_effort"] = os.getenv("GPT_OSS_REASONING", "medium")

        stream = self.client.chat.completions.create(**kwargs)
        
        # Variables pour gérer le streaming
        response_message_chunks = []
        tool_calls = []
        # Optionally capture reasoning chunks (kept internal)
        reasoning_chunks = []

        for chunk in stream:
            delta = chunk.choices[0].delta

            # Visible content
            if delta.content is not None:
                content_chunk = delta.content
                response_message_chunks.append(content_chunk)
                if print_all_output:
                    print(content_chunk, end="")

            # Reasoning stream (GPT-OSS)
            if hasattr(delta, "reasoning") and delta.reasoning:
                reasoning_chunks.append(delta.reasoning)
                if print_all_output:
                    print(delta.reasoning, end="")

            # Tool calls
            if delta.tool_calls:
                tool_calls.extend(delta.tool_calls)

        if print_all_output:
            print()  # Retour à la ligne final

        # Assembler le contenu complet
        response_message = "".join(response_message_chunks).strip()
        if not response_message:
            response_message = "Reasoning : " + "".join(reasoning_chunks).strip()
            
        # Harmony fallback: if content is empty, try a non-stream fetch for final or reasoning
        if not response_message:
            print("No response received, attempting fallback...") #for debugging
            try:
                non_stream_kwargs = dict(
                    model=model,
                    messages=messages,
                    temperature=1.1,
                    max_tokens=1000,
                    stream=False
                )
                if is_gpt_oss(model):
                    non_stream_kwargs["reasoning_effort"] = os.getenv("GPT_OSS_REASONING", "medium")

                resp = self.client.chat.completions.create(**non_stream_kwargs)
                msg = resp.choices[0].message
                response_message = (msg.content or getattr(msg, "reasoning", "") or "").strip()
            except Exception:
                # As a last resort, if we captured streamed reasoning, expose a trimmed version
                if reasoning_chunks:
                    response_message = "".join(reasoning_chunks).strip()[:800]

        return response_message, tool_calls

    async def execute_tool_call(self, tool_call, print_all_output: bool) -> str:
        """Execute a tool call and return the result"""
        tool_name = tool_call.function.name
        
        try:
            # Parse JSON string to dict more safely
            tool_args = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, ValueError) as e:
            if print_all_output:
                print(f"Warning: Failed to parse {tool_name} arguments: {e}")
            tool_args = {}

        # Execute tool call
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            tool_result = result.content[0].text if hasattr(result, 'content') else str(result)
        except Exception as e:
            if print_all_output:
                print(f"Error executing tool {tool_call.function.name}: {str(e)}")
            tool_result = "Error"

        return tool_result

    async def process_query(self, query: str, model: str, print_all_output: bool) -> str:
        """Process a query using Groq (OpenAI-compatible) and available tools"""
        messages = list(self.messages) + [{"role": "user", "content": query}]

        tools_list = await self.session.list_tools()
        available_tools = [{"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema}} for tool in tools_list.tools]
        
        response_message, tool_calls = await self.process_and_print(model, messages, available_tools, print_all_output)

        messages.append({"role": "assistant", "content": response_message})

        if not tool_calls:  # If no tool call is needed, simply print the first response (if not already printed)
            if not print_all_output:
                print("No tools needed. \n")
                print(response_message)
        
        else:
            if len(tool_calls) > 1:  # for debug/curiosity
                print(f"Multiple tool calls: \n{len(tool_calls)} tool calls detected.")
            for tool_call in tool_calls:
                tool_result = await self.execute_tool_call(tool_call, print_all_output=print_all_output)
                if print_all_output:
                    print(f"Tool call : {tool_call.function.name} was called with arguments {tool_call.function.arguments} with result: {tool_result}")

                # Simplified conversation format for better understanding
                messages.append({
                    "role": "assistant",
                    "content": f"Tool call : {tool_call.function.name} was called with arguments {tool_call.function.arguments}, with result: {tool_result}"
                })

            # Generate final response (no tools this time). This format enables to work further with the response.
            messages.append({
                "role": "assistant",
                "content": await self.process_and_print(model, messages, available_tools=None, print_all_output=True)
            })


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

                model = os.getenv("MODEL")
                print_all_output = os.getenv("PRINT_ALL_MODEL_OUTPUT", "False") == "True"
                await self.process_query(query, model, print_all_output)
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