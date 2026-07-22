# notes_tools.py — SQLite-backed notes with PDF export
from __future__ import annotations
import os
import sqlite3
from datetime import datetime
from fastmcp import FastMCP

mcp = FastMCP("notes")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "notes.db")
PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _ensure_dirs():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _init_db():
    _ensure_dirs()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


_init_db()


@mcp.tool()
def add_note(content: str) -> dict:
    """Add a new note. Returns the note id and timestamp."""
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO notes (content, created_at, updated_at) VALUES (?, ?, ?)",
            (content, now, now),
        )
        return {"status": "ok", "id": cur.lastrowid, "created_at": now}


@mcp.tool()
def get_notes() -> list[dict]:
    """List all saved notes, newest first."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, content, created_at, updated_at FROM notes ORDER BY id DESC"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@mcp.tool()
def search_notes(keyword: str) -> list[dict]:
    """Search notes by keyword (case-insensitive). Returns matching notes."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, content, created_at, updated_at FROM notes "
            "WHERE content LIKE ? ORDER BY id DESC",
            (f"%{keyword}%",),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@mcp.tool()
def export_notes_pdf() -> dict:
    """Export all notes to a PDF file. Returns the file path for download."""
    try:
        from fpdf import FPDF
    except ImportError:
        return {"status": "error", "message": "fpdf2 is not installed. Run: uv add fpdf2"}

    notes = get_notes()
    if not notes:
        return {"status": "error", "message": "No notes to export"}

    _ensure_dirs()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "My Notes", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # Subtitle with export date
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(
        0, 8,
        f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(8)

    # Notes
    for note in notes:
        # Header line
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(
            0, 7,
            f"#{note['id']}  |  {note['created_at']}",
            new_x="LMARGIN", new_y="NEXT",
        )
        # Body
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, note["content"])
        pdf.ln(4)

    out_path = os.path.join(PDF_DIR, "notes_export.pdf")
    pdf.output(out_path)
    return {"status": "ok", "path": out_path, "note_count": len(notes)}
