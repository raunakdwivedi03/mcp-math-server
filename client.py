# client.py — terminal test client for the Personal Assistant MCP server + Groq
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from groq import BadRequestError
from dotenv import load_dotenv

load_dotenv()

SERVERS = {
    "assistant": {
        "transport": "stdio",
        "command": "uv",
        "args": [
            "run",
            "fastmcp",
            "run",
            "server.py"
        ]
    }
}

SYSTEM_MSG = SystemMessage(content=(
    "You are a powerful personal assistant. You have access to these tool categories:\n"
    "• Weather — get current weather and forecasts for any city\n"
    "• Notes — add, search, list, and export notes to PDF\n"
    "• Email — check new emails, search, read, and summarize emails\n"
    "• Expenses — full expense tracking with categories and summaries\n"
    "• Browser — search the web and open URLs\n"
    "• GitHub — list issues, create issues, get latest commits\n\n"
    "Use the appropriate tool when the user's request matches a category. "
    "If the question does not require a tool, answer directly using your own knowledge. "
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
    print(f"✅ Connected! {len(named_tools)} tools available:")
    for name in sorted(named_tools.keys()):
        print(f"   • {name}")

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    # Interactive loop
    print("\n" + "=" * 50)
    print("Personal Assistant (type 'quit' to exit)")
    print("=" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye! 👋")
            break
        if not user_input:
            continue

        prompt = HumanMessage(content=user_input)
        response = await call_with_retry(llm_with_tools, [SYSTEM_MSG, prompt])

        if not getattr(response, "tool_calls", None):
            print(f"\nAssistant: {response.content}")
            continue

        tool_messages = []
        for tc in response.tool_calls:
            selected_tool = tc["name"]
            selected_tool_args = tc.get("args") or {}
            selected_tool_id = tc["id"]

            result = await named_tools[selected_tool].ainvoke(selected_tool_args)
            print(f"  🔧 {selected_tool}({selected_tool_args}) → {result}")

            tool_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=selected_tool_id,
                name=selected_tool
            ))

        final_response = await call_with_retry(
            llm_with_tools, [SYSTEM_MSG, prompt, response, *tool_messages]
        )
        print(f"\nAssistant: {final_response.content}")

if __name__ == '__main__':
    asyncio.run(main())