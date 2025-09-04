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
                "content": "You are an agentic assistant that can use tools. Planning rule: Privately plan the solution first. If tools are needed and their inputs are known, emit all required tool calls in one turn. No redundant calls: Do not call the same tool twice with identical arguments. Idempotence: Prefer arguments that make calls idempotent and cache-friendly. Termination: – If no tool is needed, answer directly. – After tool results are returned (role:tool), either batch any remaining calls (if now fully specified) or produce a clear final answer. – If information is insufficient even after tools, explain what’s missing and stop. Output contract: Never emit additional tool calls after your final answer."
            }
        ]
        # Add a small Harmony nudge only when using GPT-OSS
        model = os.getenv("MODEL")
        if is_gpt_oss(model):
            self.messages.append({
                "role": "system",
                "content": "Think privately if needed. Then ALWAYS provide a clear final answer in the assistant message body."
            })
        else: #GPT-OSS cannot return multiple tool calls at once.
            self.messages.append({
                "role": "system",
                "content": "Batching rule: Prefer one batched turn with multiple tool calls over multiple incremental turns. When not to batch: If a later tool’s inputs depend on the output of an earlier tool, call only the prerequisite tools first; otherwise batch."
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
        print("Model :", os.getenv("MODEL"))
        print("Reasoning :", os.getenv("GPT_OSS_REASONING", "medium")) if is_gpt_oss(os.getenv("MODEL")) else None
        print(f"Connected via {transport} to server with tools:", [tool.name for tool in tools])

    async def process_and_print(self, model: str, messages: list, available_tools: list, print_all_output: bool):
        """Process user query or model's past reasoning and tool calls and prints response as it gets generated.
        The model returns its thinking and its answer.
        We only return its answer and tool calls.
        If no answer, we return the thinking as its answer."""
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

        is_reasoning=True
        for chunk in stream:
            delta = chunk.choices[0].delta

            # Visible content
            if delta.content is not None:
                content_chunk = delta.content
                response_message_chunks.append(content_chunk)
                if print_all_output:
                    if not is_reasoning:
                        print("\n\nResponse:", end=" ")
                        is_reasoning=True
                    print(content_chunk, end="")

            # Reasoning stream (GPT-OSS)
            if hasattr(delta, "reasoning") and delta.reasoning:
                reasoning_chunks.append(delta.reasoning)
                if print_all_output:
                    if is_reasoning:
                        print("Reasoning:", end=" ")
                        is_reasoning=False
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

        assistant_msg = {"role": "assistant", "content": response_message}
        
        if tool_calls:
            formatted_calls = []
            for tc in tool_calls:
                formatted_calls.append({
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}"
                }
            })
                
            assistant_msg["tool_calls"] = formatted_calls
            
        return assistant_msg, tool_calls

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
            tool_result = [result.content[i].text for i in range(len(result.content))] if hasattr(result, 'content') else str(result)
        except Exception as e:
            if print_all_output:
                print(f"Error executing tool {tool_call.function.name}: {str(e)}")
            tool_result = f"[tool_error] {e}"

        # Stringify content (Harmony/Chat Completions expects a string)
        if isinstance(tool_result, (dict, list)):
            tool_content = json.dumps(tool_result, ensure_ascii=False)
        else:
            tool_content = "" if tool_result is None else str(tool_result)
            
        return tool_content

    async def process_query(self, query: str, model: str, print_all_output: bool, max_iters: int=8) -> str:
        """Process a query using Groq (OpenAI-compatible) and MCP tools in an agent loop."""
        messages = list(self.messages) + [{"role": "user", "content": query}]

        tools_list = await self.session.list_tools()
        available_tools = [{"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema}} for tool in tools_list.tools]
        
        for step in range(max_iters):
            if print_all_output:
                print(f"\n[Iteration:] {step+1}/{max_iters}")

            # 2.a) Call the model with tools enabled
            assistant_msg, tool_calls = await self.process_and_print(model=model, messages=messages, available_tools=available_tools, print_all_output=print_all_output)
            messages.append(assistant_msg)
            
            # 2.b) If no tools requested → final answer, stop. We print the response only if not already printed.
            if not tool_calls:
                if not print_all_output:
                    print("Final Response: ", assistant_msg["content"])
                return

            # 2.c) If tools requested, the user approves before they are called
            if print_all_output:
                print("")
            user_approval = input(f"The model wants to call {', '.join(tc.function.name for tc in tool_calls)}. Do you approve? (y/n): ").strip().lower()
            if user_approval.lower() == 'y':
                # Execute each tool call and push a `role:"tool"` message for each
                if print_all_output:
                    print("Number of tool calls:", len(tool_calls))
                for tc in tool_calls:
                    name = tc.function.name
                    raw_args = tc.function.arguments

                    tool_content = await self.execute_tool_call(tc, print_all_output=print_all_output)

                    # Append the tool message (required fields)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": tool_content
                    })

                    if print_all_output:
                        print(f"[Tool call:] {name}({raw_args}) -> {tool_content}")
            else:
                user_request = "Tool call was not approved." + input("Please guide the model's next steps:")
                messages.append({"role": "user", "content": user_request})


        # 3) If we exit by max_iters, try to finalize with a last non-tool turn
        print(f"\n[agent] reached max_iters={max_iters}; forcing a finalization turn.")
        messages.append({"role": "user", "content": "You have reached maximum number of iterations. Do produce a final answer. You may not call any more tools."})
        start = time.time()
        final_answer, _ = await self.process_and_print(
            model=model,
            messages=messages,
            available_tools=None,                 # deactivate tools to force the model to conclude
            print_all_output=True
        )
        print(f"Final Response Time: {time.time() - start:.2f} seconds")


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