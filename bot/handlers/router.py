"""Intent router — routes plain-text messages through the LLM tool-calling loop."""

import asyncio
import json
import sys

from services.llm_client import LLMClient
from services.lms_client import LMSClient

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "List all labs and tasks. Use ONLY when you need the list of lab IDs. If the user mentions a specific lab number (e.g. 'lab 3', 'lab-03'), skip this and call the relevant tool directly with lab='lab-03'.",
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
            "description": "Get score distribution for a lab",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string", "description": "Lab ID e.g. 'lab-04'"}},
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab. For comparing pass rates across all labs, call this for each lab ID simultaneously.",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string", "description": "Lab ID e.g. 'lab-04'"}},
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
                "properties": {"lab": {"type": "string", "description": "Lab ID e.g. 'lab-04'"}},
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group average scores and student counts for a lab. Call directly with the lab ID when a lab number is mentioned.",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string", "description": "Lab ID e.g. 'lab-03'"}},
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
                    "lab": {"type": "string", "description": "Lab ID e.g. 'lab-04'"},
                    "limit": {"type": "integer", "description": "Number of top learners (default 5)"},
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
                "properties": {"lab": {"type": "string", "description": "Lab ID e.g. 'lab-04'"}},
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
    "You are an LMS assistant bot. Use tools to fetch real data, then answer.\n\n"
    "Rules:\n"
    "1. If the user specifies a lab number (e.g. 'lab 3', 'lab-03', 'lab 4'), call the relevant "
    "tool DIRECTLY with that lab ID — do NOT call get_items first.\n"
    "2. For 'which lab has the lowest/highest pass rate': call get_items once to get lab IDs, "
    "then call get_pass_rates for EVERY lab in ONE response (multiple tool calls at once).\n"
    "3. Always include specific numbers (percentages) AND lab names in your final answer. "
    "Format: 'Lab 03 has the lowest pass rate at 52.3%'. Never omit the percentage.\n"
    "4. For greetings or unrelated input, respond helpfully and mention what you can do."
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

    for _ in range(8):
        msg = await llm.chat(messages, tools=TOOLS)
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            return msg.get("content") or "I couldn't generate a response."

        messages.append(msg)

        # Execute all tool calls in parallel
        async def exec_tc(tc: dict) -> tuple[str, str, str]:
            name = tc["function"]["name"]
            args = json.loads(tc["function"].get("arguments", "{}"))
            print(f"[tool] LLM called: {name}({args})", file=sys.stderr)
            result = await _call_tool(name, args, lms)
            count = len(json.loads(result)) if result.startswith("[") else "-"
            print(f"[tool] Result: {count} items", file=sys.stderr)
            return tc["id"], name, result

        results = await asyncio.gather(*[exec_tc(tc) for tc in tool_calls])
        print(f"[summary] Feeding {len(results)} tool result(s) back to LLM", file=sys.stderr)

        for tool_id, _name, result in results:
            messages.append({"role": "tool", "tool_call_id": tool_id, "content": result})

    return "Could not complete the request after multiple steps."


def get_tool_names() -> list[str]:
    """Return list of available tool names (for documentation)."""
    return [t["function"]["name"] for t in TOOLS]
