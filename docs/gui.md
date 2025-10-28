# Watchpath GUI Guide

The Watchpath desktop application wraps the same log-analysis pipeline as the CLI with a playful
PySide6 (Qt) interface. Launch it with `watchpath gui` or by calling
[`watchpath.gui.launch_gui`](../src/watchpath/gui/__init__.py) from your own code. The main window is
implemented in [`watchpath/gui/app.py`](../src/watchpath/gui/app.py).

## Launching the app

```bash
watchpath gui [log_path] [--model MODEL] [--chunk-size N] [--prompt PROMPT]
```

- `log_path` (optional) preloads a log file as soon as the window opens.
- `--model`, `--chunk-size`, and `--prompt` seed the default values in the toolbar controls.
- If the GUI is launched without arguments you can open logs later using the **Open Log 🍡** toolbar
  action or by dragging files into the window.

Make sure Qt (PySide6) and the Ollama CLI are installed in your environment. When the GUI starts it
creates a `QApplication`, applies the default dark theme, and waits for user input.

## Layout overview

The interface is divided into three primary areas:

1. **Toolbar** — Located at the top (`_build_toolbar`). It provides:
   - **Open Log 🍡** to choose a log file.
   - **Stop ⏹** to cancel the current background analysis after the active session completes.
   - A **model** combo box listing common Ollama models (editable for custom entries).
   - A **chunk size** spin box for how many log lines per session go to the model.
   - A **Prompt ✨** button to swap the base prompt template.
   - An **Anomaly threshold** slider (“vibe slider”) that hides sessions below the chosen score.
   - A **theme toggle** button for switching between light and dark palettes.
2. **Global statistics card** — A panel produced by `GlobalStatsWidget` that summarises mean session
   duration, HTTP method mix, and the most frequent IPs. It gently animates when new stats arrive.
3. **Session workspace** — A horizontal splitter containing:
   - The **session carousel** (`SessionListWidget`), showing each analysed session as a card with
     anomaly score, request count, and emoji severity.
   - The **session detail view** (`SessionDetailWidget`) where you inspect the selected session’s
     summary, Mochi risk meter, analyst note, evidence, raw logs, and Markdown export.

Status updates and progress live in the status bar at the bottom. A determinate progress bar appears
while analysis is running and hides once complete.

## How analysis runs

When you open or drop a log file, `KawaiiMainWindow.load_log_file` spins up an `AnalysisWorker` on a
`QThread` so the UI stays responsive. The worker pipeline matches the CLI:

1. Validates the log and prompt files.
2. Parses sessions with `load_sessions` and calculates global statistics (`summarize_sessions`).
3. Streams each session back to the UI after calling `analyze_logs_ollama_chunk` with the configured
   chunk size, model, and prompt.
4. Emits structured payloads consumed by the widgets. If Ollama fails, the worker falls back to a
   textual error message and still shows the log excerpt for manual review.

You can stop analysis mid-way with the **Stop ⏹** button. The worker honours the request after the
current session finishes and the UI keeps all results collected so far.

## Exploring sessions

- Selecting a card in the session carousel updates the detail pane via `_handle_session_selected`.
- The Mochi meter in `SessionDetailWidget` classifies risk bands (`safe`, `low`, `medium`, `high`) and
  recolours the progress bar and mascot accordingly.
- The “Evidence” tab renders model-supplied evidence, and the “Logs” tab shows the raw chunk fed into
  the LLM. A Markdown tab exposes the exact Markdown text used by the CLI.
- Adjust the anomaly threshold slider to focus on higher-risk sessions. Hidden cards disappear from the
  carousel but remain in memory and reappear when the threshold lowers again.

## Themes and vibes

Two themes ship with the app (`THEME_CONFIGS`): a default dark palette and a light alternative. The
**☀️/🌙** button flips between them, recolouring the entire window and the Mochi meter styling. The
vibe slider’s threshold is displayed in the status bar every time it changes.

## Drag and drop

You can drag log files from your file manager straight onto the window. The window accepts local file
URLs in `dragEnterEvent`/`dropEvent` and then reuses `load_log_file` for analysis.

## Integration with the CLI

The GUI consumes the same payload structure emitted by `watchpath parse --output-format=json`. Each
`ProcessedSession` holds the JSON payload along with ready-to-display text and Markdown reports, so the
CLI and GUI stay consistent for automation, reporting, and UI usage alike. Switching between the two
interfaces is largely a matter of preference.
