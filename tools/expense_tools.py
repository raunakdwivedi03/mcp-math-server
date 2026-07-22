# expense_tools.py — SQLite-backed expense tracking (ported from Expense_tracker_MCP_server)
from __future__ import annotations
import os
import sqlite3
from fastmcp import FastMCP

mcp = FastMCP("expenses")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "categories.db")


def _ensure_dirs():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _init_db():
    _ensure_dirs()
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
    with sqlite3.connect(CATEGORIES_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                monthly_budget REAL DEFAULT 0
            )
        """)


_init_db()


@mcp.tool()
def add_expense(
    date: str, amount: float, category: str,
    subcategory: str = "", note: str = ""
) -> dict:
    """Add a new expense entry. Date should be YYYY-MM-DD format."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) "
            "VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note),
        )
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
def list_expenses(start_date: str = "", end_date: str = "") -> list[dict]:
    """List expense entries, optionally filtered by a date range (YYYY-MM-DD)."""
    with sqlite3.connect(DB_PATH) as c:
        query = "SELECT id, date, amount, category, subcategory, note FROM expenses"
        params: list = []
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        query += " ORDER BY id ASC"
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def get_expense(expense_id: int) -> dict:
    """Fetch a single expense entry by its id."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "SELECT id, date, amount, category, subcategory, note "
            "FROM expenses WHERE id = ?",
            (expense_id,),
        )
        row = cur.fetchone()
        if row is None:
            return {"status": "error", "message": f"No expense with id {expense_id}"}
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


@mcp.tool()
def update_expense(
    expense_id: int,
    date: str = "", amount: float = 0,
    category: str = "", subcategory: str = "", note: str = "",
) -> dict:
    """Update one or more fields of an existing expense entry."""
    fields = {
        "date": date, "amount": amount, "category": category,
        "subcategory": subcategory, "note": note,
    }
    updates = {k: v for k, v in fields.items() if v}
    if not updates:
        return {"status": "error", "message": "No fields provided to update"}

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [expense_id]

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?", params
        )
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense with id {expense_id}"}
        return {"status": "ok", "id": expense_id, "updated_fields": list(updates.keys())}


@mcp.tool()
def delete_expense(expense_id: int) -> dict:
    """Delete an expense entry by its id."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense with id {expense_id}"}
        return {"status": "ok", "deleted_id": expense_id}


@mcp.tool()
def list_categories() -> list[str]:
    """List all distinct categories currently used in expenses."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "SELECT DISTINCT category FROM expenses ORDER BY category ASC"
        )
        return [r[0] for r in cur.fetchall()]


@mcp.tool()
def add_category(name: str, monthly_budget: float = 0) -> dict:
    """Add a predefined category with an optional monthly budget."""
    with sqlite3.connect(CATEGORIES_PATH) as c:
        try:
            c.execute(
                "INSERT INTO categories(name, monthly_budget) VALUES (?, ?)",
                (name, monthly_budget),
            )
            return {"status": "ok", "name": name}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": f"Category '{name}' already exists"}


@mcp.tool()
def list_defined_categories() -> list[dict]:
    """List all predefined categories with their monthly budgets."""
    with sqlite3.connect(CATEGORIES_PATH) as c:
        cur = c.execute(
            "SELECT id, name, monthly_budget FROM categories ORDER BY name ASC"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def delete_category(name: str) -> dict:
    """Delete a predefined category by name."""
    with sqlite3.connect(CATEGORIES_PATH) as c:
        cur = c.execute("DELETE FROM categories WHERE name = ?", (name,))
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No category named '{name}'"}
        return {"status": "ok", "deleted": name}


@mcp.tool()
def summarize_by_category(start_date: str = "", end_date: str = "") -> list[dict]:
    """Total spend grouped by category, optionally filtered by date range."""
    with sqlite3.connect(DB_PATH) as c:
        query = (
            "SELECT category, SUM(amount) as total, COUNT(*) as count "
            "FROM expenses"
        )
        params: list = []
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        query += " GROUP BY category ORDER BY total DESC"
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def summarize_by_month(year: str = "") -> list[dict]:
    """Total spend grouped by month (YYYY-MM), optionally filtered to a year."""
    with sqlite3.connect(DB_PATH) as c:
        query = (
            "SELECT strftime('%Y-%m', date) as month, "
            "SUM(amount) as total, COUNT(*) as count FROM expenses"
        )
        params: list = []
        if year:
            query += " WHERE strftime('%Y', date) = ?"
            params = [str(year)]
        query += " GROUP BY month ORDER BY month ASC"
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def get_total(start_date: str = "", end_date: str = "") -> dict:
    """Get the total amount spent, optionally filtered by date range."""
    with sqlite3.connect(DB_PATH) as c:
        query = "SELECT SUM(amount), COUNT(*) FROM expenses"
        params: list = []
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        cur = c.execute(query, params)
        total, count = cur.fetchone()
        return {"total": total or 0.0, "count": count}
