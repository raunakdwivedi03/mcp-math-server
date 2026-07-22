# github_tools.py — GitHub REST API tools (issues, commits)
from __future__ import annotations
import os
import requests
from fastmcp import FastMCP

mcp = FastMCP("github")

API_BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _parse_repo(repo: str) -> str:
    """Normalise 'owner/repo' or full URL to 'owner/repo'."""
    repo = repo.strip().rstrip("/")
    if repo.startswith("https://github.com/"):
        repo = repo.replace("https://github.com/", "")
    return repo


@mcp.tool()
def list_open_issues(repo: str, count: int = 10) -> list[dict]:
    """List open issues for a GitHub repository.

    `repo` should be in 'owner/repo' format (e.g. 'facebook/react').
    """
    repo = _parse_repo(repo)
    resp = requests.get(
        f"{API_BASE}/repos/{repo}/issues",
        headers=_headers(),
        params={"state": "open", "per_page": count, "sort": "updated", "direction": "desc"},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {
            "number": issue["number"],
            "title": issue["title"],
            "user": issue["user"]["login"],
            "labels": [l["name"] for l in issue.get("labels", [])],
            "created_at": issue["created_at"],
            "url": issue["html_url"],
        }
        for issue in resp.json()
        if "pull_request" not in issue  # exclude PRs
    ]


@mcp.tool()
def create_issue(repo: str, title: str, body: str = "") -> dict:
    """Create a new issue on a GitHub repository.

    Requires a GITHUB_TOKEN with repo scope in .env.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {
            "status": "error",
            "message": "GITHUB_TOKEN is required to create issues. Add it to .env.",
        }

    repo = _parse_repo(repo)
    resp = requests.post(
        f"{API_BASE}/repos/{repo}/issues",
        headers=_headers(),
        json={"title": title, "body": body},
        timeout=10,
    )
    if resp.status_code == 201:
        data = resp.json()
        return {
            "status": "ok",
            "number": data["number"],
            "url": data["html_url"],
        }
    return {
        "status": "error",
        "code": resp.status_code,
        "message": resp.json().get("message", resp.text),
    }


@mcp.tool()
def get_latest_commits(repo: str, count: int = 10) -> list[dict]:
    """Fetch the most recent commits from a GitHub repository."""
    repo = _parse_repo(repo)
    resp = requests.get(
        f"{API_BASE}/repos/{repo}/commits",
        headers=_headers(),
        params={"per_page": count},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {
            "sha": c["sha"][:7],
            "message": c["commit"]["message"].split("\n")[0],
            "author": c["commit"]["author"]["name"],
            "date": c["commit"]["author"]["date"],
            "url": c["html_url"],
        }
        for c in resp.json()
    ]
