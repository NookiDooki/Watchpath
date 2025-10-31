# Watchpath Overview

Watchpath helps security and operations teams inspect web server access logs for anomalous visitor
sessions. The project provides both a command-line interface (CLI) and a PySide6-based GUI that share
the same log parsing, statistics, and LLM analysis pipeline.

> 🧭 **Start here:** The [main README](README.md) showcases screenshots, workflows, and quick-start
> commands. Use this overview when you need a structural map or want to extend the core modules.

- For terminal workflows, follow the [CLI guide](cli.md).
- For an interactive desktop experience, see the [GUI guide](gui.md).
- For command recipes and API samples, visit [Usage recipes](usage.md).

## Architecture at a glance

```
┌────────────┐    ┌────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ Access log │ →  │ Session parser │ →  │ Session statistics   │ →  │ Ollama LLM analysis │
└────────────┘    │ (`parser.py`)  │    │ (`summarize_sessions`) │  │ (`ai.py`)           │
                  └────────────────┘    └─────────────────────┘    └─────────────────────┘
                          │                                           │
                          └────────── Shared JSON payload ────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
             CLI renderer (`cli.py`)                 GUI widgets (`gui/app.py`)
```

Both interfaces read the same session payloads and stay in sync on how scores, analyst notes, and
supporting evidence are displayed.

## Core components

| Component | Location | Responsibility |
| --- | --- | --- |
| CLI | [`src/watchpath/cli.py`](../src/watchpath/cli.py) | Argument parsing, command routing, report formatting, and Rich rendering. |
| GUI | [`src/watchpath/gui/main_window.py`](../src/watchpath/gui/main_window.py) | PySide6 widgets, threading, theming, and interactive controls. |
| Parser | [`src/watchpath/parser.py`](../src/watchpath/parser.py) | Log parsing, session grouping, report formatting helpers, and JSON payload creation. |
| AI integration | [`src/watchpath/ai.py`](../src/watchpath/ai.py) | Invokes the Ollama CLI, parses responses, and normalises model output. |
| API | [`src/watchpath/api.py`](../src/watchpath/api.py) | FastAPI wrapper for automation scenarios or third-party integrations. |
| Entry points | [`src/main.py`](../src/main.py), [`src/watchpath/__main__.py`](../src/watchpath/__main__.py) | Provide `python -m watchpath` compatibility and forward to the CLI. |

## Data flow

1. **Log ingestion** — The parser reads Apache/Nginx-style access logs, converts rows into `LogRecord`
   objects, and groups them into visitor sessions (`Session`).
2. **Statistics** — `summarize_sessions` captures aggregate metrics (mean duration, request mix,
   IP distribution) reused by both interfaces.
3. **LLM analysis** — For each session, `build_session_chunk` selects the first *N* log lines which are
   sent to `analyze_logs_ollama_chunk` together with the base prompt template.
4. **Payload building** — `build_session_payload` assembles everything into a JSON-friendly structure.
5. **Presentation** — The CLI formats the payload as text, Markdown, or JSON; the GUI decorates it in
   widgets with additional UX (Mochi meter, vibe slider, themes).

## Configuration and prompts

The base prompt template lives at `prompts/base_prompt.txt`. Both interfaces accept a `--prompt` option
(or prompt chooser in the GUI) so that teams can tune instructions for their models. Model and chunk
size defaults are identical across interfaces to keep behaviour predictable.

## Extensibility tips

> 💡 Pair this section with the [Usage recipes](usage.md) document for real-world command snippets.

- **Automation** — Use `watchpath parse --output-format=json` to feed the structured payload into other
  systems. The GUI consumes the exact same structure (`ProcessedSession.payload`).
- **Custom prompts** — Maintain multiple prompt templates and point either interface at the one you need
  for a given investigation. The [Prompt Manager](../src/watchpath/ui/prompt_manager.py) exposes overrides in the GUI.
- **Model swaps** — Both interfaces only require the Ollama model name; as long as the model is pulled
  locally it will work across CLI and GUI.
- **Session limits** — The CLI trims processing to five sessions by default; adjust log files or extend
  the code if you need bulk processing. The GUI currently processes every session until stopped.

## Next steps

1. Read the [CLI guide](cli.md) for automation and scripting workflows.
2. Dive into the [GUI guide](gui.md) to learn about the Mochi Observatory interface.
3. Explore the [Usage recipes](usage.md) for copy-paste commands and API payloads.
4. Return to the [main README](README.md) whenever you need a visual overview or updated quick starts.
