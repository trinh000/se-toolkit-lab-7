"""Intent router — routes plain-text messages through the LLM tool-calling loop."""

import json
import sys

from services.llm_client import LLMClient
from services.lms_client import LMSClient

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "List all labs and tasks available in the LMS",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "List enrolled students and their groups",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution (4 buckets: 0-25%, 25-50%, 50-75%, 75-100%) for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get number of submissions per day for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group average scores and student counts for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners by score for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"},
                    "limit": {"type": "integer", "description": "Number of top learners to return (default 5)"},
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get the completion rate percentage for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Refresh data from the autochecker (ETL sync)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

SYSTEM_PROMPT = (
    "You are an LMS assistant bot. You have access to tools that fetch data from a "
    "Learning Management System backend. When a user asks a question, use the appropriate "
    "tools to get data, then provide a clear and concise answer. "
    "For multi-step questions (e.g. 'which lab has the lowest pass rate'), call tools "
    "for each lab and compare the results. Always use tools to answer data questions — "
    "do not guess. If the question is a greeting or unrelated, respond helpfully and "
    "mention what you can do."
)


async def _call_tool(name: str, args: dict, lms: LMSClient) -> str:
    try:
        if name == "get_items":
            result = await lms.get_items()
        elif name == "get_learners":
            result = await lms.get_learners()
        elif name == "get_scores":
            result = await lms.get_scores(**args)
        elif name == "get_pass_rates":
            result = await lms.get_pass_rates(**args)
        elif name == "get_timeline":
            result = await lms.get_timeline(**args)
        elif name == "get_groups":
            result = await lms.get_groups(**args)
        elif name == "get_top_learners":
            result = await lms.get_top_learners(**args)
        elif name == "get_completion_rate":
            result = await lms.get_completion_rate(**args)
        elif name == "trigger_sync":
            result = await lms.trigger_sync()
        else:
            return f"Unknown tool: {name}"
        return json.dumps(result)
    except Exception as e:
        return f"Error calling {name}: {e}"


async def route(text: str, lms: LMSClient, llm: LLMClient) -> str:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    for _ in range(10):  # max iterations to prevent infinite loops
        msg = await llm.chat(messages, tools=TOOLS)
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            return msg.get("content") or "I couldn't generate a response."

        # Execute all tool calls
        messages.append(msg)
        for tc in tool_calls:
            name = tc["function"]["name"]
            args = json.loads(tc["function"].get("arguments", "{}"))
            print(f"[tool] LLM called: {name}({args})", file=sys.stderr)
            result = await _call_tool(name, args, lms)
            item_count = len(json.loads(result)) if result.startswith("[") else "-"
            print(f"[tool] Result: {item_count} items", file=sys.stderr)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

        print(f"[summary] Feeding {len(tool_calls)} tool result(s) back to LLM", file=sys.stderr)

    return "Could not complete the request after multiple steps."
