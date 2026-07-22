# server.py — Unified FastMCP server registering all tool modules
from __future__ import annotations
from dotenv import load_dotenv
from fastmcp import FastMCP

# Ensure environment variables from .env are loaded
load_dotenv()

# ── Create the main server ──────────────────────────────────────────
mcp = FastMCP("PersonalAssistant")

# ── Import tool sub-servers and mount them ──────────────────────────
from tools.weather_tools import mcp as weather_mcp
from tools.notes_tools import mcp as notes_mcp
from tools.email_tools import mcp as email_mcp
from tools.expense_tools import mcp as expense_mcp
from tools.browser_tools import mcp as browser_mcp
from tools.github_tools import mcp as github_mcp

# Mount each sub-server with its namespace
mcp.mount(weather_mcp, namespace="weather")
mcp.mount(notes_mcp, namespace="notes")
mcp.mount(email_mcp, namespace="email")
mcp.mount(expense_mcp, namespace="expenses")
mcp.mount(browser_mcp, namespace="browser")
mcp.mount(github_mcp, namespace="github")

if __name__ == "__main__":
    mcp.run()
