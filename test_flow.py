# test_flow.py — End-to-end test: MCP server + Groq API
import asyncio
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

load_dotenv()

SERVERS = {
    "assistant": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8000/mcp"
    }
}


async def test():
    print("=" * 60)
    print("  PERSONAL ASSISTANT — End-to-End Test")
    print("=" * 60)

    # ── Step 1: Connect ──────────────────────────────────────────
    print("\n📡 STEP 1: Connecting to MCP server...")
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()
    named = {t.name: t for t in tools}
    print(f"  ✅ {len(named)} tools found:")
    for name in sorted(named.keys()):
        print(f"     • {name}")

    # ── Step 2: LLM ──────────────────────────────────────────────
    print("\n🤖 STEP 2: Setting up Groq LLM...")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    print("  ✅ LLM ready")

    sys_msg = SystemMessage(content=(
        "You are a personal assistant with weather, notes, email, expense, "
        "browser, and github tools. Use them when appropriate."
    ))

    # ── Step 3: Test Weather ─────────────────────────────────────
    print("\n🌤️  STEP 3: Testing weather — 'What's the weather in London?'")
    prompt = HumanMessage(content="What's the weather in London?")
    response = await llm_with_tools.ainvoke([sys_msg, prompt])
    if response.tool_calls:
        tool_messages = []
        for tc in response.tool_calls:
            result = await named[tc["name"]].ainvoke(tc.get("args", {}))
            print(f"  🔧 {tc['name']}({tc.get('args', {})}) = {result}")
            tool_messages.append(ToolMessage(
                content=str(result), tool_call_id=tc["id"], name=tc["name"]
            ))
        final = await llm_with_tools.ainvoke([sys_msg, prompt, response] + tool_messages)
        print(f"  ✅ Answer: {final.content[:200]}")
    else:
        print(f"  ℹ️  Direct answer: {response.content[:200]}")

    # ── Step 4: Test Notes ───────────────────────────────────────
    print("\n📝 STEP 4: Testing notes — 'Save a note: Test note from e2e test'")
    prompt = HumanMessage(content="Save a note: Test note from e2e test")
    response = await llm_with_tools.ainvoke([sys_msg, prompt])
    if response.tool_calls:
        tool_messages = []
        for tc in response.tool_calls:
            result = await named[tc["name"]].ainvoke(tc.get("args", {}))
            print(f"  🔧 {tc['name']}({tc.get('args', {})}) = {result}")
            tool_messages.append(ToolMessage(
                content=str(result), tool_call_id=tc["id"], name=tc["name"]
            ))
        final = await llm_with_tools.ainvoke([sys_msg, prompt, response] + tool_messages)
        print(f"  ✅ Answer: {final.content[:200]}")
    else:
        print(f"  ℹ️  Direct answer: {response.content[:200]}")

    # ── Step 5: Test Web Search ──────────────────────────────────
    print("\n🌐 STEP 5: Testing browser — 'Search the web for FastMCP Python'")
    prompt = HumanMessage(content="Search the web for FastMCP Python")
    response = await llm_with_tools.ainvoke([sys_msg, prompt])
    if response.tool_calls:
        tool_messages = []
        for tc in response.tool_calls:
            result = await named[tc["name"]].ainvoke(tc.get("args", {}))
            print(f"  🔧 {tc['name']}({tc.get('args', {})}) = {result}")
            tool_messages.append(ToolMessage(
                content=str(result), tool_call_id=tc["id"], name=tc["name"]
            ))
        final = await llm_with_tools.ainvoke([sys_msg, prompt, response] + tool_messages)
        print(f"  ✅ Answer: {final.content[:200]}")
    else:
        print(f"  ℹ️  Direct answer: {response.content[:200]}")

    print("\n" + "=" * 60)
    print("  ALL TESTS COMPLETE!")
    print("=" * 60)


asyncio.run(test())
