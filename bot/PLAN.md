# Bot Development Plan

## Overview

This bot provides a Telegram interface to the LMS backend. Users can check system
health, browse labs, view scores, and ask questions in plain language. The bot is
designed with a testable handler architecture: command logic lives in pure functions
that know nothing about Telegram, making offline testing trivial via `--test` mode.

## Architecture

The bot is split into three layers:

1. **Transport layer** (`bot.py`) — connects to Telegram via aiogram and dispatches
   incoming messages to handlers. In `--test` mode, it calls handlers directly and
   prints the result to stdout, then exits.

2. **Handler layer** (`handlers/`) — pure async functions that accept typed arguments
   (command text, an LMS client instance) and return plain strings. No Telegram objects
   here. This makes them testable without a Telegram connection.

3. **Service layer** (`services/`) — thin HTTP clients that wrap the LMS backend API
   and the LLM API. Handlers call services; services call external APIs.

Configuration is loaded once at startup via `config.py` using `pydantic-settings`,
which reads from `.env.bot.secret`.

## Task breakdown

### Task 1 — Scaffold (this task)

Create the directory structure, `pyproject.toml`, `config.py`, stub handlers for
`/start`, `/help`, `/health`, `/labs`, `/scores`, and wire up `--test` mode in
`bot.py`. Verify all commands run offline.

### Task 2 — Backend integration

Implement `services/lms_client.py` with real HTTP calls to the LMS API. Wire handlers
to real data: `/health` calls `GET /health`, `/labs` calls `GET /items/`, `/scores`
calls `GET /analytics/task-pass-rate` filtered by lab.

### Task 3 — Intent routing

Add `services/llm_client.py` wrapping the Qwen Code API (OpenAI-compatible). Implement
a router in `handlers/router.py` that sends plain-text messages to the LLM with a
system prompt listing available tools, parses the LLM response, and dispatches to the
right handler.

### Task 4 — Containerize

Add a `Dockerfile` for the bot and add a `bot` service to `docker-compose.yml`.
The bot reads `LMS_API_URL=http://backend:8000` inside Docker. Document deployment
in the README.

## Testing strategy

Every handler is tested in `--test` mode before being wired to Telegram. After each
task, the sequence is: `uv run bot.py --test "/command"` locally → `git push` →
`git pull` on VM → restart bot → verify in Telegram.
