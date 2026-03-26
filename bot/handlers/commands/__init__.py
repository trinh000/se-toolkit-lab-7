"""Command handlers — pure async functions, no Telegram dependency."""

import httpx

from services.lms_client import LMSClient


def _fmt_error(e: Exception) -> str:
    if isinstance(e, httpx.ConnectError):
        return f"❌ Backend error: connection refused. Check that the services are running. ({e})"
    if isinstance(e, httpx.HTTPStatusError):
        return f"❌ Backend error: HTTP {e.response.status_code}. The backend service may be down."
    if isinstance(e, httpx.TimeoutException):
        return f"❌ Backend error: request timed out. ({e})"
    return f"❌ Backend error: {e}"


async def handle_start() -> str:
    return (
        "👋 Welcome to LMS Bot!\n\n"
        "I connect you to the LMS backend — check health, browse labs, view scores.\n\n"
        "Type /help to see available commands."
    )


async def handle_help() -> str:
    return (
        "Available commands:\n\n"
        "/start — welcome message\n"
        "/help — show this list\n"
        "/health — check backend status and item count\n"
        "/labs — list available labs\n"
        "/scores <lab-id> — per-task pass rates (e.g. /scores lab-04)\n\n"
        "You can also send plain text and I'll route it (Task 3)."
    )


async def handle_health(client: LMSClient) -> str:
    try:
        items = await client.get_items()
        return f"✅ Backend is healthy. {len(items)} items available."
    except Exception as e:
        return _fmt_error(e)


async def handle_labs(client: LMSClient) -> str:
    try:
        items = await client.get_items()
    except Exception as e:
        return _fmt_error(e)

    labs = [i for i in items if i.get("type") == "lab"]
    if not labs:
        return "No labs found."

    lines = ["Available labs:\n"]
    for lab in labs:
        lines.append(f"- {lab['title']}")
    return "\n".join(lines)


async def handle_scores(lab: str, client: LMSClient) -> str:
    if not lab:
        return "Usage: /scores <lab-id>  (e.g. /scores lab-04)"

    try:
        rows = await client.get_pass_rates(lab=lab)
    except Exception as e:
        return _fmt_error(e)

    if not rows:
        return f"No score data found for lab '{lab}'."

    lines = [f"Pass rates for {lab}:\n"]
    for row in rows:
        task = row.get("task", "?")
        score = row.get("avg_score")
        attempts = row.get("attempts", 0)
        if score is not None:
            lines.append(f"- {task}: {score:.1f}% ({attempts} attempts)")
        else:
            lines.append(f"- {task}: n/a")
    return "\n".join(lines)
