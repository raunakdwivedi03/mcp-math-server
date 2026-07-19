# app.py — Streamlit chat UI for the MCP math server + Groq
import os
import sys
import asyncio
import streamlit as st
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from groq import BadRequestError
from dotenv import load_dotenv

load_dotenv()

# Works both locally (.env) and on Streamlit Cloud (secrets)
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass  # No secrets.toml locally — fine, .env will be used instead

# Cross-platform server config — uses same Python interpreter, relative path
SERVERS = {
    "math": {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["main.py"]
    }
}

SYSTEM_MSG = SystemMessage(content=(
    "You are a helpful assistant. You have access ONLY to these tools: "
    "add, subtract, multiply, divide. "
    "If the user's question does not require one of these tools, "
    "answer directly using your own knowledge. "
    "Never invent or call a tool that is not in your tool list."
))

st.set_page_config(page_title="MCP Math Assistant", page_icon="🧮")
st.title("🧮 MCP Math Assistant")
st.caption("Powered by FastMCP + LangChain + Groq")

if "messages" not in st.session_state:
    st.session_state.messages = []


async def call_with_retry(llm_with_tools, messages, retries=2):
    last_error = None
    for attempt in range(retries + 1):
        try:
            return await llm_with_tools.ainvoke(messages)
        except BadRequestError as e:
            last_error = e
    raise last_error


async def get_tools_and_llm():
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()
    named_tools = {tool.name: tool for tool in tools}
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    return named_tools, llm_with_tools


async def run_agent(user_input: str):
    named_tools, llm_with_tools = await get_tools_and_llm()

    prompt = HumanMessage(content=user_input)
    response = await call_with_retry(llm_with_tools, [SYSTEM_MSG, prompt])

    if not getattr(response, "tool_calls", None):
        return response.content, None

    tool_messages = []
    tool_log = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]

        result = await named_tools[selected_tool].ainvoke(selected_tool_args)
        tool_log.append(f"🔧 **{selected_tool}**({selected_tool_args}) → `{result}`")

        tool_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=selected_tool_id,
            name=selected_tool
        ))

    final_response = await call_with_retry(
        llm_with_tools, [SYSTEM_MSG, prompt, response, *tool_messages]
    )
    return final_response.content, tool_log


# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_log"):
            with st.expander("Tool calls"):
                for line in msg["tool_log"]:
                    st.markdown(line)

# Chat input
user_input = st.chat_input("Ask a math question or anything else...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                content, tool_log = asyncio.run(run_agent(user_input))
            except BadRequestError:
                content = "⚠️ The model had trouble processing that. Please try rephrasing your question."
                tool_log = None

        st.markdown(content)
        if tool_log:
            with st.expander("Tool calls"):
                for line in tool_log:
                    st.markdown(line)

    st.session_state.messages.append({
        "role": "assistant",
        "content": content,
        "tool_log": tool_log
    })