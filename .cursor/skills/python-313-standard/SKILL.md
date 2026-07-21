---
name: python-313-standard
description: >-
  Enforces Python 3.13+, efficient algorithms (prefer O(1)/O(n)/O(n log n) over
  O(n²)), and project coding standards for the Medical Expert AI Chat service.
  Use when writing, reviewing, or refactoring Python code in this repo, changing
  dependencies, or when the user mentions Python version, complexity, pyproject.toml,
  or project conventions.
---

# Python 3.13 Standard

## Non-negotiables

1. **Python 3.13+ only** — keep `requires-python = ">=3.13"` in `pyproject.toml`
2. **Do not downgrade** to 3.10/3.11/3.12 for convenience; install 3.13 via `uv` or deadsnakes instead
3. **No Docker** — run with venv + `medical-chat` / uvicorn
4. **Run and test with 3.13** — use `.venv` created from Python 3.13
5. **Prefer fast algorithms** — avoid O(n²) when O(n), O(n log n), or O(log n) is realistic

## Algorithmic complexity (required)

When writing or reviewing code that searches, aggregates, or looks up data:

| Prefer | Avoid |
|---|---|
| `dict` / `set` lookup → **O(1)** avg | scanning a list for membership → **O(n)** |
| sorted + binary search → **O(log n)** | nested loops over the same data → **O(n²)** |
| single pass / hash map → **O(n)** | repeated full scans → **O(n²)** |
| heap / sorted structure when needed → **O(n log n)** | bubble/selection-style nested loops |

Rules:

- For **lookup by id/key**, use `dict` (this project already does for `MessageStore`)
- For **membership checks**, prefer `set`/`dict` over `list` scans
- Do **not** introduce nested loops over growing collections when a map/set/sort fixes it
- Keep solutions simple: pick the right structure first; do not add heavy frameworks just for big-O
- Hot paths (workers, queue, rate limiter, store, stats): keep them **O(1)** or **O(n)** per operation, never accidental **O(n²)**

## Language and typing (3.13-native)

Prefer built-in syntax over backports:

| Use | Avoid |
|---|---|
| `str \| None` | `Optional[str]` from `typing` |
| `list[str]`, `dict[str, int]` | `List`, `Dict` from `typing` |
| `StrEnum` from `enum` | string constants or `Enum` hacks |
| `match` / `case` for status branching | long `if/elif` chains when clearer |

Do not add `from __future__ import annotations` unless required — native 3.13 annotations are enough.

## Project layout

```
src/medical_chat/     # application package (src layout)
tests/                # pytest integration tests
static/               # frontend assets
.cursor/skills/       # project coding standards
```

- New modules go under `src/medical_chat/`
- Keep `main.py` thin; routes in `api.py`, business logic in dedicated modules
- Config via `Settings` (`pydantic-settings`) with env var aliases — never hardcode secrets
- Do not add Dockerfiles or docker-compose

## Stack conventions

| Layer | Standard |
|---|---|
| HTTP | FastAPI + uvicorn (`--factory`) |
| Config | `pydantic-settings` + `.env` |
| Async workers | `asyncio` queue + worker pool |
| LLM clients | `llm/` package with factory pattern |
| Tests | `pytest` + `pytest-asyncio` + `httpx` + `asgi-lifespan` |

When adding endpoints, include `/health` for health checks.

## Code style

- Google-style clarity: small focused functions, minimal scope
- Match existing naming (`message_id`, `worker_pool`, `snake_case` files)
- Use dataclasses for internal domain objects; Pydantic models for API I/O
- Thread-safe storage/logging with explicit locks for shared mutable state
- Comments only for non-obvious business or concurrency behavior
## Environment variables

All runtime config goes through `Settings` in `config.py`. When adding new config:

1. Add field with `Field(alias="ENV_NAME")`
2. Document in `.env.example` and `README.md`
3. Provide a sensible default when safe

## Before finishing changes

Run validation:

```bash
python .cursor/skills/python-313-standard/scripts/validate.py
pytest
```

Fix any failures before considering the task done.

## Common rejections

- Lowering `requires-python` below 3.13
- Using sync blocking calls in async route handlers without `asyncio.to_thread`
- Adding dependencies without updating `pyproject.toml`
- Skipping tests for new API behavior
- Putting API keys or secrets in source code
- Reintroducing Docker packaging
- O(n²) nested scans when a `dict`/`set`/sort would make it O(n) or O(n log n)

## Python 3.13 setup (when missing)

```bash
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.13
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Reference

- Assignment API contract: `POST /chat`, `GET /chat/{messageId}`, `GET /statistics`
- Run: `medical-chat` or uvicorn factory; health at `GET /health`
