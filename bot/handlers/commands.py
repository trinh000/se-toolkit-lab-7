"""Command handlers — pure async functions, no Telegram dependency."""

from services.lms_client import LMSClient


async def handle_start() -> str:
    return (
        "👋 Welcome to the LMS Bot!\n\n"
        "I can help you check system health, browse labs, and view scores.\n\n"
        "Type /help to see available commands."
    )


async def handle_help() -> str:
    return (
        "Available commands:\n\n"
        "/start — welcome message\n"
        "/help — show this list\n"
        "/health — check backend status\n"
        "/labs — list available labs\n"
        "/scores <lab-id> — show task pass rates for a lab\n\n"
        "You can also send plain text and I'll try to help (Task 3)."
    )


async def handle_health(client: LMSClient) -> str:
    ok = await client.health()
    if ok:
        return "✅ Backend is up and running."
    return "❌ Backend is not responding. Please try again later."


async def handle_labs(client: LMSClient) -> str:
    try:
        items = await client.get_items()
    except Exception as e:
        return f"❌ Could not fetch labs: {e}"

    labs = [i for i in items if i.get("type") == "lab"]
    if not labs:
        return "No labs found."

    lines = ["Available labs:\n"]
    for lab in labs:
        lines.append(f"• {lab['title']}")
    return "\n".join(lines)


async def handle_scores(lab: str, client: LMSClient) -> str:
    if not lab:
        return "Usage: /scores <lab-id>  (e.g. /scores lab-04)"

    try:
        rows = await client.get_task_pass_rate(lab=lab)
    except Exception as e:
        return f"❌ Could not fetch scores: {e}"

    if not rows:
        return f"No score data found for lab '{lab}'."

    lines = [f"Pass rates for {lab}:\n"]
    for row in rows:
        title = row.get("title", row.get("task", "?"))
        rate = row.get("pass_rate")
        if rate is not None:
            lines.append(f"• {title}: {rate:.0%}")
        else:
            lines.append(f"• {title}: n/a")
    return "\n".join(lines)
