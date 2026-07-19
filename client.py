# client.py — terminal test client for the MCP math server + Groq
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from groq import BadRequestError
from dotenv import load_dotenv

load_dotenv()

SERVERS = {
    "math": {
        "transport": "stdio",
        "command": "D:/python311/Scripts/uv.exe",
        "args": [
            "run",
            "fastmcp",
            "run",
            "D:/yt client/main.py"
        ]
    }
}

SYSTEM_MSG = SystemMessage(content=(
    "You are a helpful assistant. You have access ONLY to these tools: "
    "add, subtract, multiply, divide. "
    "If the user's question does not require one of these tools, "
    "answer directly using your own knowledge. "
    "Never invent or call a tool that is not in your tool list."
))


async def call_with_retry(llm_with_tools, messages, retries=2):
    last_error = None
    for attempt in range(retries + 1):
        try:
            return await llm_with_tools.ainvoke(messages)
        except BadRequestError as e:
            last_error = e
            print(f"⚠️ tool_use_failed, retrying... (attempt {attempt + 1})")
    raise last_error


async def main():
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    named_tools = {tool.name: tool for tool in tools}
    print(named_tools)

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    prompt = HumanMessage(content="What is the product of 12 and 15, and also the sum of 5 and 7?")
    response = await call_with_retry(llm_with_tools, [SYSTEM_MSG, prompt])

    if not getattr(response, "tool_calls", None):
        print("\nLLM Reply:", response.content)
        return

    tool_messages = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]

        result = await named_tools[selected_tool].ainvoke(selected_tool_args)
        print(f"Tool called: {selected_tool} | Args: {selected_tool_args} | Result: {result}")

        tool_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=selected_tool_id,
            name=selected_tool
        ))

    final_response = await call_with_retry(
        llm_with_tools, [SYSTEM_MSG, prompt, response, *tool_messages]
    )
    print(f"Final response: {final_response.content}")

if __name__ == '__main__':
    asyncio.run(main())