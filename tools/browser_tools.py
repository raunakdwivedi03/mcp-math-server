# browser_tools.py — Web search and URL opener
from __future__ import annotations
import webbrowser
from fastmcp import FastMCP

mcp = FastMCP("browser")


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo. Returns titles, URLs, and snippets."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return [{"error": "duckduckgo-search is not installed. Run: uv add duckduckgo-search"}]

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
    return results


@mcp.tool()
def open_url(url: str) -> dict:
    """Open a URL in the default web browser."""
    try:
        webbrowser.open(url)
        return {"status": "ok", "url": url, "message": f"Opened {url} in the default browser."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
