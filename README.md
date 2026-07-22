# 🚀 Personal Assistant MCP Server & Executive Workspace

An enterprise-grade, multi-tool AI assistant powered by **FastMCP**, **LangChain**, **Groq LLM (Llama 3.3 70B)**, and **Streamlit**.

---

## 🛠️ Operational Tool Modules (27 Active Tools)

1. **🌤️ Weather Services** (`tools/weather_tools.py`)
   - `weather_get_weather`: Current weather metrics with automatic zero-config fallback (Open-Meteo).
   - `weather_get_forecast`: Multi-day weather forecasts.

2. **📝 Notes & Documents** (`tools/notes_tools.py`)
   - `notes_add_note`: Add notes with auto-timestamps (SQLite backed).
   - `notes_get_notes`: List saved notes.
   - `notes_search_notes`: Keyword search across notes.
   - `notes_export_notes_pdf`: Export notes to PDF with direct download.

3. **📧 Email Integration** (`tools/email_tools.py`)
   - `email_check_new_emails`: Fetch unread emails via Gmail IMAP.
   - `email_search_emails`: Search inbox by subject/body keywords.
   - `email_get_email_content`: Fetch full email body.
   - `email_summarize_email`: Generate concise email summaries via Groq.

4. **💰 Expense Tracker** (`tools/expense_tools.py`)
   - Complete SQLite financial engine for expenses, categories, budget tracking, monthly summaries, and total spend calculations.

5. **🌐 Web Intelligence** (`tools/browser_tools.py`)
   - `browser_search_web`: Web search via DuckDuckGo.
   - `browser_open_url`: Open links in default browser.

6. **🐙 GitHub Workspace** (`tools/github_tools.py`)
   - `github_list_open_issues`: List repository issues.
   - `github_get_latest_commits`: Retrieve commit logs.
   - `github_create_issue`: Create issues via GitHub REST API.

---

## 💻 Local Setup & Running

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/raunakdwivedi03/mcp-math-server.git
cd mcp-math-server
uv sync
```

### 2. Environment Variables (`.env`)
Create a `.env` file with your credentials:
```env
GROQ_API_KEY=your_groq_api_key
OPENWEATHERMAP_API_KEY=your_openweather_key
GITHUB_TOKEN=your_github_pat_token
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
IMAP_SERVER=imap.gmail.com
```

### 3. Run Locally
- **FastMCP Server**: `uv run fastmcp run server.py --transport streamable-http --port 8000`
- **Streamlit Console**: `uv run streamlit run app.py`

---

## ☁️ Deployment on Render.com

This repository includes `launcher.py` and `render.yaml` for seamless deployment as a single Web Service on Render:

1. Connect your repository `raunakdwivedi03/mcp-math-server` on **Render**.
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `python launcher.py`
4. Add your environment variables in the Render dashboard.
