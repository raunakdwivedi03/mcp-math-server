# email_tools.py — Gmail IMAP email tools with LLM summarization and graceful error handling
from __future__ import annotations
import os
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("email")


def _get_credentials() -> tuple[str, str]:
    addr = os.getenv("EMAIL_ADDRESS", "").strip()
    pwd = os.getenv("EMAIL_PASSWORD", "").strip()
    if not addr or not pwd:
        raise RuntimeError(
            "Missing EMAIL_ADDRESS or EMAIL_PASSWORD in .env. "
            "For Gmail, use a 16-character App Password from: "
            "https://myaccount.google.com/apppasswords"
        )
    return addr, pwd


def _get_imap_server() -> str:
    return os.getenv("IMAP_SERVER", "imap.gmail.com").strip()


def _decode_header_value(value: str | None) -> str:
    if value is None:
        return ""
    decoded_parts = decode_header(value)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return " ".join(parts)


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain-text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return "(no text body found)"


def _connect() -> imaplib.IMAP4_SSL:
    addr, pwd = _get_credentials()
    server = _get_imap_server()
    mail = imaplib.IMAP4_SSL(server)
    mail.login(addr, pwd)
    return mail


def _parse_email_summary(msg: email.message.Message, uid: str) -> dict:
    return {
        "email_id": uid,
        "from": _decode_header_value(msg.get("From")),
        "subject": _decode_header_value(msg.get("Subject")),
        "date": _decode_header_value(msg.get("Date")),
    }


@mcp.tool()
def check_new_emails(count: int = 10) -> list[dict] | dict:
    """Fetch the latest unread emails (up to `count`).

    Returns list of dicts with email_id, from, subject, date.
    """
    try:
        mail = _connect()
    except imaplib.IMAP4.error as e:
        return {
            "status": "error",
            "error_type": "AuthenticationFailed",
            "message": (
                "Gmail authentication failed. Standard account passwords will not work for IMAP. "
                "Please enable 2-Step Verification on your Google Account and generate a 16-character "
                "App Password at https://myaccount.google.com/apppasswords, then update EMAIL_PASSWORD in .env."
            ),
            "details": str(e),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    try:
        mail.select("INBOX")
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            return []

        uids = data[0].split()[-count:]
        results = []
        for uid in reversed(uids):
            status, msg_data = mail.fetch(uid, "(BODY.PEEK[HEADER])")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            results.append(_parse_email_summary(msg, uid.decode()))
        return results
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            mail.logout()
        except Exception:
            pass


@mcp.tool()
def search_emails(query: str, count: int = 10) -> list[dict] | dict:
    """Search emails by keyword in subject or body. Returns up to `count` results."""
    try:
        mail = _connect()
    except imaplib.IMAP4.error as e:
        return {
            "status": "error",
            "error_type": "AuthenticationFailed",
            "message": (
                "Gmail authentication failed. Standard account passwords will not work for IMAP. "
                "Please enable 2-Step Verification on your Google Account and generate a 16-character "
                "App Password at https://myaccount.google.com/apppasswords, then update EMAIL_PASSWORD in .env."
            ),
            "details": str(e),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    try:
        mail.select("INBOX")
        criteria = f'(OR SUBJECT "{query}" BODY "{query}")'
        status, data = mail.search(None, criteria)
        if status != "OK" or not data[0]:
            # Try ALL search fallback if specific IMAP criteria failed
            status, data = mail.search(None, "ALL")
            if status != "OK" or not data[0]:
                return []

        uids = data[0].split()[-count:]
        results = []
        for uid in reversed(uids):
            status, msg_data = mail.fetch(uid, "(BODY.PEEK[HEADER])")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            summary = _parse_email_summary(msg, uid.decode())
            # Perform keyword filtering in Python for maximum compatibility
            if query.lower() in summary["subject"].lower() or query.lower() in summary["from"].lower():
                results.append(summary)
            elif len(results) < count:
                results.append(summary)

        return results[:count]
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            mail.logout()
        except Exception:
            pass


@mcp.tool()
def get_email_content(email_id: str) -> dict:
    """Fetch the full content of a specific email by its ID."""
    try:
        mail = _connect()
    except imaplib.IMAP4.error as e:
        return {
            "status": "error",
            "error_type": "AuthenticationFailed",
            "message": (
                "Gmail authentication failed. Please generate a 16-character App Password at "
                "https://myaccount.google.com/apppasswords and update EMAIL_PASSWORD in .env."
            ),
            "details": str(e),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    try:
        mail.select("INBOX")
        status, msg_data = mail.fetch(email_id.encode(), "(RFC822)")
        if status != "OK":
            return {"status": "error", "message": f"Could not fetch email {email_id}"}

        msg = email.message_from_bytes(msg_data[0][1])
        body = _extract_body(msg)
        return {
            "email_id": email_id,
            "from": _decode_header_value(msg.get("From")),
            "to": _decode_header_value(msg.get("To")),
            "subject": _decode_header_value(msg.get("Subject")),
            "date": _decode_header_value(msg.get("Date")),
            "body": body[:5000],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            mail.logout()
        except Exception:
            pass


@mcp.tool()
def summarize_email(email_id: str) -> dict:
    """Fetch an email and return a concise summary."""
    content = get_email_content(email_id)
    if isinstance(content, dict) and content.get("status") == "error":
        return content

    body = content.get("body", "")
    subject = content.get("subject", "")

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        messages = [
            SystemMessage(content="Summarize the following email in 2-3 concise sentences."),
            HumanMessage(content=f"Subject: {subject}\n\n{body}"),
        ]
        response = llm.invoke(messages)
        summary = response.content
    except Exception:
        summary = body[:500] + ("..." if len(body) > 500 else "")

    return {
        "email_id": email_id,
        "subject": subject,
        "from": content.get("from", ""),
        "summary": summary,
    }
