# Medical Expert AI Chat

Self-contained Python **3.13+** service with an HTTP API, async LLM workers, interaction logging, statistics, and a simple UI.

---

## Requirements

- **Python 3.13+**
- `uv` (recommended) **or** `pip` + `python3.13-venv`

---

## Install and run

### 1. Install Python 3.13 (if needed)

**Option A — uv (no sudo):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.13
```

**Option B — Ubuntu (deadsnakes):**

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13 python3.13-venv
```

### 2. Create a virtualenv and install the app

```bash
cd /path/to/oneDoc

# with uv
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# or with pip
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

Default settings use the **mock LLM** (no API key needed).

To use a real provider, edit `.env`:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# or
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run the server

```bash
source .venv/bin/activate
medical-chat
```

Or:

```bash
uvicorn medical_chat.main:create_app --factory --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** for the UI.

Health check:

```bash
curl http://localhost:8000/health
```

Stop with `Ctrl+C`.

---

## Verify with the API

```bash
# Submit a question
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What are the symptoms of iron deficiency?"}'

# Poll for the answer (replace MESSAGE_ID)
curl -s http://localhost:8000/chat/MESSAGE_ID

# Statistics
curl -s http://localhost:8000/statistics
```

---

## Run tests

```bash
source .venv/bin/activate
pytest
```

---

## Configuration reference

Set these in `.env` (see `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `SERVER_PORT` | HTTP port | `8000` |
| `LLM_PROVIDER` | `mock` / `openai` / `anthropic` | `mock` |
| `LLM_MODEL` | Model name | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | Sampling temperature | `0.3` |
| `LLM_MAX_TOKENS` | Max tokens per response | `1024` |
| `RETRY_DELAY` | Seconds between retries | `1.0` |
| `MAX_RETRIES` | Max retry attempts | `3` |
| `WORKER_IDLE_TIMEOUT` | Idle worker shutdown (seconds) | `30` |
| `LOG_FILE` | Interaction log path | `logs/interactions.log` |
| `ENFORCE_MEDICAL_ONLY` | Reject non-medical questions | `true` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `20` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window | `60` |
| `OPENAI_API_KEY` | Required for OpenAI | — |
| `ANTHROPIC_API_KEY` | Required for Anthropic | — |

---

## Project layout

```
src/medical_chat/      # Application code
static/index.html      # Simple UI
tests/                 # pytest tests
.env.example           # Config template
docs/architecture.pdf  # Architecture overview
.cursor/skills/        # Project coding standards
```

---

## Disclaimer

This service is a technical assignment. It does **not** provide real medical advice.
