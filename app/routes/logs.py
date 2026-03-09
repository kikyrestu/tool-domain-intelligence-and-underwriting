"""Log viewer routes — view pipeline logs in browser."""

import os
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "pipeline.log")
MAX_LINES = 200


@router.get("/logs")
async def log_viewer(request: Request):
    return templates.TemplateResponse("logs/viewer.html", {"request": request})


@router.get("/logs/content")
async def log_content(lines: int = MAX_LINES):
    """Return last N lines of the pipeline log as plain text (for HTMX polling)."""
    if not os.path.exists(LOG_FILE):
        return PlainTextResponse("No log file yet. Run a crawl to generate logs.")
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:]
        return PlainTextResponse("".join(tail))
    except Exception as e:
        return PlainTextResponse(f"Error reading log: {e}")


@router.post("/logs/clear")
async def clear_logs():
    """Clear the pipeline log file."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
    return PlainTextResponse("Log cleared.")
