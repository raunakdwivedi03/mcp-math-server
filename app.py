# app.py — High-Aesthetic Enterprise Workspace for FastMCP + Groq
import os
import json
import asyncio
import nest_asyncio
import streamlit as st
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from groq import BadRequestError
from dotenv import load_dotenv

# Patch the event loop so asyncio.run() works inside Streamlit
nest_asyncio.apply()

load_dotenv()

# Load API credentials from secrets or .env
try:
    for key in ("GROQ_API_KEY", "OPENWEATHERMAP_API_KEY", "GITHUB_TOKEN",
                "EMAIL_ADDRESS", "EMAIL_PASSWORD"):
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass

# Remote MCP server config
SERVERS = {
    "assistant": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8000/mcp"
    }
}

TOOL_CATEGORIES = {
    "Weather Services": ["weather_get_weather", "weather_get_forecast"],
    "Notes & Documents": ["notes_add_note", "notes_get_notes", "notes_search_notes", "notes_export_notes_pdf"],
    "Email Integration": ["email_check_new_emails", "email_search_emails", "email_get_email_content", "email_summarize_email"],
    "Expense Tracker": [
        "expenses_add_expense", "expenses_list_expenses", "expenses_get_expense",
        "expenses_update_expense", "expenses_delete_expense",
        "expenses_list_categories", "expenses_add_category",
        "expenses_list_defined_categories", "expenses_delete_category",
        "expenses_summarize_by_category", "expenses_summarize_by_month", "expenses_get_total",
    ],
    "Web Intelligence": ["browser_search_web", "browser_open_url"],
    "GitHub Workspace": ["github_list_open_issues", "github_create_issue", "github_get_latest_commits"],
}

SYSTEM_MSG = SystemMessage(content=(
    "You are an enterprise AI assistant connected to a high-performance MCP server. "
    "You have access to 6 core operational modules: Weather Services, Notes & Documents, "
    "Email Integration, Expense Tracker, Web Intelligence, and GitHub Workspace.\n"
    "Execute tool calls whenever specific data or action is requested. "
    "ALWAYS provide a clear, helpful final text response summarizing the tool output. "
    "Never return an empty response."
))

# ── Page Configuration ─────────────────────────────────────────────
st.set_page_config(
    page_title="Executive AI Console",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── High-Aesthetic Glassmorphism CSS ────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main Canvas Styling */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #111827 0%, #030712 100%);
        color: #f3f4f6;
    }
    
    /* Hide Streamlit Default Elements */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    
    /* Header Banner */
    .hero-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
    }
    
    .hero-title {
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 6px 0;
    }
    
    .hero-subtitle {
        font-size: 0.875rem;
        color: #94a3b8;
        font-weight: 400;
        margin: 0;
    }
    
    .hero-glow {
        position: absolute;
        top: -40px;
        right: -40px;
        width: 180px;
        height: 180px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(0, 0, 0, 0) 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    
    /* Status Badge & Pulse */
    .status-container {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 9999px;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: #34d399;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 18px;
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        }
        70% {
            transform: scale(1);
            box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
        }
        100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
        }
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0b0f17 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    .sidebar-section-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin: 20px 0 12px 0;
    }
    
    .tool-chip {
        font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
        font-size: 0.72rem;
        color: #94a3b8;
        background: rgba(30, 41, 59, 0.5);
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        margin: 2px 4px 4px 0;
        display: inline-block;
        transition: all 0.2s ease;
    }
    
    .tool-chip:hover {
        border-color: rgba(99, 102, 241, 0.4);
        color: #e2e8f0;
        background: rgba(99, 102, 241, 0.1);
    }
    
    /* Custom Expander Styling */
    .stExpander {
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        background: rgba(15, 23, 42, 0.4) !important;
        margin-bottom: 8px !important;
        transition: border-color 0.2s ease;
    }
    
    .stExpander:hover {
        border-color: rgba(99, 102, 241, 0.3) !important;
    }
    
    /* Chat Input Bar Refinement */
    .stChatInputContainer {
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(12px) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Download Button Modern Styling */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.01em !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.45) !important;
    }
    
    /* Chat Message Bubbles */
    div[data-testid="stChatMessage"] {
        background: rgba(15, 23, 42, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 14px !important;
        padding: 16px !important;
        margin-bottom: 12px !important;
    }
    
    div[data-testid="stChatMessage"]:nth-child(even) {
        background: rgba(30, 41, 59, 0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ── Sidebar Content ────────────────────────────────────────────────
with st.sidebar:
    st.markdown('''
        <div class="status-container">
            <div class="pulse-dot"></div>
            <span>MCP Cluster Connected</span>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("<h2 style='font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin: 0;'>Control Console</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.8rem; color: #64748b; margin-top: 2px; margin-bottom: 20px;'>FastMCP Microservice Architecture</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-section-title">Active Domain Capabilities</div>', unsafe_allow_html=True)
    
    for category, tools in TOOL_CATEGORIES.items():
        with st.expander(category):
            for t in tools:
                clean_name = t.split("_", 1)[1] if "_" in t else t
                st.markdown(f'<div class="tool-chip">{clean_name}</div>', unsafe_allow_html=True)
                
    st.markdown("---")
    st.markdown("""
        <div style='background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.75rem; color: #64748b;'>
            <div style='color: #94a3b8; font-weight: 600; margin-bottom: 4px;'>Endpoint Reference</div>
            <code>http://127.0.0.1:8000/mcp</code>
        </div>
    """, unsafe_allow_html=True)

# ── Hero Section ────────────────────────────────────────────────────
st.markdown("""
    <div class="hero-container">
        <div class="hero-glow"></div>
        <h1 class="hero-title">Executive AI Workspace</h1>
        <p class="hero-subtitle">High-performance client interface • 27 operational tools active</p>
    </div>
""", unsafe_allow_html=True)

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
    """Connect to MCP server, fetch tools, and bind them to the LLM."""
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()
    named_tools = {tool.name: tool for tool in tools}
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    return named_tools, llm_with_tools


def _format_fallback_content(tool_messages: list) -> str:
    """Format tool output as human-readable text if LLM returns empty string."""
    parts = []
    for tm in tool_messages:
        try:
            parsed = json.loads(tm.content)
            if isinstance(parsed, list):
                if not parsed:
                    parts.append("No items found.")
                else:
                    parts.append(f"**Found {len(parsed)} item(s):**\n")
                    for idx, item in enumerate(parsed, 1):
                        if isinstance(item, dict):
                            fields = ", ".join(f"**{k}**: `{v}`" for k, v in item.items())
                            parts.append(f"{idx}. {fields}")
                        else:
                            parts.append(f"{idx}. `{item}`")
            elif isinstance(parsed, dict):
                fields = "\n".join(f"- **{k}**: `{v}`" for k, v in parsed.items())
                parts.append(fields)
            else:
                parts.append(str(parsed))
        except Exception:
            parts.append(str(tm.content))
    return "\n\n".join(parts)


async def run_agent(user_input: str):
    named_tools, llm_with_tools = await get_tools_and_llm()

    prompt = HumanMessage(content=user_input)
    response = await call_with_retry(llm_with_tools, [SYSTEM_MSG, prompt])

    if not getattr(response, "tool_calls", None):
        return response.content, None, None

    tool_messages = []
    tool_log = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]

        result = await named_tools[selected_tool].ainvoke(selected_tool_args)
        tool_log.append(f"Function: `{selected_tool}`\nArguments: `{selected_tool_args}`\nReturn: `{result}`")

        tool_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=selected_tool_id,
            name=selected_tool
        ))

    final_response = await call_with_retry(
        llm_with_tools, [SYSTEM_MSG, prompt, response, *tool_messages]
    )

    final_content = getattr(final_response, "content", "") or ""
    if not final_content.strip():
        final_content = _format_fallback_content(tool_messages)

    pdf_path = None
    for tm in tool_messages:
        if "notes_export" in str(tm.name) and "path" in tm.content:
            try:
                data = json.loads(tm.content)
                if isinstance(data, dict) and "path" in data:
                    pdf_path = data["path"]
            except Exception:
                pass

    return final_content, tool_log, pdf_path


# Render message history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_log"):
            with st.expander("Execution Trace"):
                for line in msg["tool_log"]:
                    st.markdown(line)
        if msg.get("pdf_path") and os.path.exists(msg["pdf_path"]):
            with open(msg["pdf_path"], "rb") as f:
                st.download_button(
                    "Download PDF Document",
                    f.read(),
                    file_name="notes_export.pdf",
                    mime="application/pdf",
                )

# Chat Input
user_input = st.chat_input("Ask a question or execute a command...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Executing instruction..."):
            try:
                result = asyncio.run(run_agent(user_input))
                content = result[0]
                tool_log = result[1]
                pdf_path = result[2] if len(result) > 2 else None
            except BadRequestError:
                content = "System Error: The request could not be processed. Please rephrase."
                tool_log = None
                pdf_path = None
            except Exception as e:
                content = f"Execution Error: {str(e)}"
                tool_log = None
                pdf_path = None

        st.markdown(content)
        if tool_log:
            with st.expander("Execution Trace"):
                for line in tool_log:
                    st.markdown(line)
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Download PDF Document",
                    f.read(),
                    file_name="notes_export.pdf",
                    mime="application/pdf",
                )

    st.session_state.messages.append({
        "role": "assistant",
        "content": content,
        "tool_log": tool_log,
        "pdf_path": pdf_path,
    })