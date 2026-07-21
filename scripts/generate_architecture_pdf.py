#!/usr/bin/env python3
"""Generate docs/architecture.pdf for the current Medical Expert AI Chat design."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parents[1] / "docs" / "architecture.pdf"


class ArchitecturePDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, "Medical Expert AI Chat - Architecture", align="L")
        self.ln(4)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str) -> None:
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(20, 20, 20)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def mono_block(self, text: str) -> None:
        self.set_fill_color(245, 245, 245)
        self.set_draw_color(210, 210, 210)
        self.set_font("Courier", "", 7.5)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        y = self.get_y()
        lines = text.splitlines() or [""]
        line_h = 3.8
        h = max(12, len(lines) * line_h + 6)
        if y + h > self.page_break_trigger:
            self.add_page()
            y = self.get_y()
        self.rect(x, y, 190, h, style="DF")
        self.set_xy(x + 3, y + 3)
        for line in lines:
            self.cell(184, line_h, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(x + 3)
        self.set_y(y + h + 4)

    def kv_table(self, rows: list[tuple[str, str]], col1: float = 55) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(230, 230, 230)
        self.cell(col1, 7, "Item", border=1, fill=True)
        self.cell(190 - col1, 7, "Description", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        fill = False
        for left, right in rows:
            self.set_fill_color(250, 250, 250)
            self.set_font("Helvetica", "B", 9)
            self.cell(col1, 7, left[:40], border=1, fill=fill)
            self.set_font("Helvetica", "", 9)
            display = right if len(right) < 95 else right[:92] + "..."
            self.cell(190 - col1, 7, display, border=1, fill=fill, new_x="LMARGIN", new_y="NEXT")
            fill = not fill
        self.ln(3)


def build() -> Path:
    pdf = ArchitecturePDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Medical Expert AI Chat", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "Current system architecture", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.section_title("1. High-level architecture")
    pdf.body(
        "Python 3.13 FastAPI service with async worker pool, SQLite persistence, "
        "conversation history (agent-mode), SSE streaming, medical guardrails, "
        "input sanitization, rate limiting, shared file logs, and statistics."
    )
    pdf.mono_block(
        """
+------------------+          +--------------------------------------------------+
| Browser UI /     |  HTTP    | FastAPI (uvicorn)                                |
| curl / clients   | -------> | POST /chat                                       |
+------------------+          | GET  /chat/{id}                                  |
         |                    | GET  /chat/{id}/stream  (SSE)                    |
         | EventSource        | GET  /statistics  GET /health                    |
         +------------------> +---------+----------------------------------------+
                                        |
           +----------------------------+----------------------------+
           |                            |                            |
           v                            v                            v
  +----------------+          +------------------+          +------------------+
  | RateLimiter    |          | Sanitization     |          | Guardrails       |
  | (per-IP)       |          | UUID + text clean|          | medical-only     |
  +----------------+          +------------------+          +--------+---------+
                                                                     |
                                                                     v
                                                          +------------------+
                                                          | MessageStore     |
                                                          | dict O(1) lookup |
                                                          +--------+---------+
                                                                   |
                                              +--------------------+--------------------+
                                              |                    |                    |
                                              v                    v                    v
                                   +----------------+   +----------------+   +----------------+
                                   | MessageQueue   |   | SqlitePersist. |   | StreamHub      |
                                   | asyncio.Queue  |   | data/*.db      |   | SSE fan-out    |
                                   +--------+-------+   +----------------+   +--------+-------+
                                            |                                         ^
                                            v                                         |
                                 +---------------------------+                        |
                                 | WorkerPool                |------------------------+
                                 | max workers = CPU cores   |
                                 | retries + idle timeout    |
                                 | conversation history -> LLM
                                 +-------------+-------------+
                                               |
                     +-------------------------+-------------------------+
                     |                         |                         |
                     v                         v                         v
              +-------------+           +-------------+           +-------------+
              | Mock LLM    |           | OpenAI      |           | Anthropic   |
              +-------------+           +-------------+           +-------------+
                     |
                     +----> SharedLog (JSONL) + StatisticsCollector
""".strip(
            "\n"
        )
    )

    pdf.section_title("2. Request lifecycle")
    pdf.body(
        "POST /chat validates and sanitizes input, optionally continues a conversation, "
        "persists the message, enqueues work, and returns messageId + conversationId. "
        "Clients poll GET /chat/{id} or stream GET /chat/{id}/stream."
    )
    pdf.mono_block(
        """
  User            API              Sanitize/Guard     Store/Queue/DB        Worker           LLM/Stream
   |               |                     |                  |                 |                |
   |-- POST /chat ->|                     |                  |                 |                |
   |               |-- rate limit ------->|                  |                 |                |
   |               |-- UUID + clean text->|                  |                 |                |
   |               |-- medical-only ----->|                  |                 |                |
   |               |-- create+upsert -------------------> SQLite             |                |
   |               |-- enqueue -------------------------> Queue              |                |
   |<- ids --------|                     |                  |                 |                |
   |               |                     |                  |<-- dequeue -----|                |
   |               |                     |                  |                 |-- history ---->|
   |               |                     |                  |                 |-- stream ----->|
   |-- SSE stream ------------------------------------------- tokens/done <---|                |
   |-- GET /chat/{id} -------------------- status/answer <---|                 |                |
""".strip(
            "\n"
        )
    )

    pdf.add_page()
    pdf.section_title("3. Module map")
    pdf.kv_table(
        [
            ("main.py", "App factory, lifespan, static UI"),
            ("api.py", "HTTP routes + SSE stream"),
            ("config.py", "Env Settings (pydantic-settings)"),
            ("sanitization.py", "UUID checks, text/null-byte cleaning"),
            ("guardrails.py", "Reject non-medical / abusive input"),
            ("rate_limit.py", "Per-IP sliding-window limiter"),
            ("storage.py", "In-memory store + queue + file log"),
            ("persistence.py", "SQLite upsert/load across restarts"),
            ("stream_hub.py", "Fan-out token/done/error events"),
            ("worker_pool.py", "Workers, retries, history, idle exit"),
            ("statistics.py", "O(1) metrics counters"),
            ("llm/", "mock / OpenAI / Anthropic clients"),
            ("static/", "UI with agent-mode + EventSource"),
        ]
    )

    pdf.section_title("4. Design choices")
    pdf.kv_table(
        [
            ("Async processing", "API returns immediately; workers run in background"),
            ("Agent-mode", "Optional conversationId; prior Q&A sent to LLM"),
            ("Persistence", "SQLite (bound params); MessageStore dict for O(1)"),
            ("Streaming", "SSE token/done/error via StreamHub"),
            ("Safety", "Sanitize + UUID validate; no string-built SQL"),
            ("Concurrency", "asyncio queue + tasks; max = CPU cores"),
            ("Logs", "Append-only JSON lines file (thread-safe)"),
            ("Config", "Environment variables via Settings"),
            ("Deploy", "venv + medical-chat / uvicorn; GET /health"),
            ("Python", "Requires Python 3.13+"),
        ]
    )

    pdf.section_title("5. Data status lifecycle")
    pdf.mono_block(
        """
  pending  -->  processing  -->  completed
                          \\-->  failed

  Each transition updates MessageStore + SQLite.
  Completed/failed also append SharedLog, update Statistics, and emit StreamHub done/error.
""".strip(
            "\n"
        )
    )

    pdf.section_title("6. HTTP API")
    pdf.kv_table(
        [
            ("POST /chat", "Submit question (+ optional conversationId)"),
            ("GET /chat/{id}", "processing | completed+answer | failed+error"),
            ("GET /chat/{id}/stream", "SSE: token / done / error"),
            ("GET /statistics", "Queue, workers, retries, tokens, timings"),
            ("GET /health", "Health check"),
            ("GET /", "Simple chat UI"),
        ]
    )

    pdf.section_title("7. Safety notes")
    pdf.body(
        "User input is sanitized (NFKC, control/null stripping, length bounds). "
        "conversationId and messageId must be UUIDs. SQLite uses only bound parameters. "
        "Conversation history reused in prompts is re-sanitized and capped."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(path)
