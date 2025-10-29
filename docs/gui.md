# Watchpath GUI Guide

The Watchpath desktop application wraps the same log-analysis pipeline as the CLI with a playful
PySide6 (Qt) interface. Launch it with `watchpath gui` or by calling
[`watchpath.gui.launch_gui`](../src/watchpath/gui/__init__.py) from your own code. The main window lives
in [`watchpath/gui/main_window.py`](../src/watchpath/gui/main_window.py) and composes reusable widgets
from [`watchpath/ui`](../src/watchpath/ui).

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
   - **Re-run with alternate parameters** to respawn the worker with a different model, chunk size, or
     prompt template.
   - **Stop analysis** to cancel the current background processing.
   - A **theme toggle** for switching between the bundled dark and light palettes.
2. **Global statistics card** — Powered by `GlobalStatsWidget`. It now shows sparklines for request
   timelines, bar charts for status codes, and a combobox to swap between overview summaries.
3. **Session workspace** — A horizontal splitter containing three panels:
   - The **session list** (`SessionListWidget`) with quick search, multi-select, and method/IP/score
     filters.
   - The **session detail view** (`SessionDetailWidget`) featuring editable analyst notes, tagging,
     sortable request timelines, evidence/log search, export buttons, and side-by-side diffing.
   - A vertical stack combining the **recent analyses** sidebar (`RecentAnalysesSidebar`) and the
     **prompt manager** (`PromptManagerPanel`) for template previews, version history, and per-session
     overrides.

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

- Selecting one or more cards in the session list updates the detail pane. Multi-select lets you apply
  prompt overrides to multiple sessions at once.
- The detail view surfaces model, chunk, and prompt metadata directly under the session title.
- Tabs present evidence, raw logs, and Markdown with dedicated copy/export controls. Search boxes
  highlight matches in evidence and logs, while the diff tab compares any two sources.
- The timeline table can display either the per-session request sequence or the global distribution
  computed by the worker.
- Analyst notes are editable `QTextEdit`s with tagging and assignment controls. Saving a note persists it
  for the lifetime of the window, even after prompt overrides.

## Themes and prompt overrides

The light/dark theme toggle adjusts a simple stylesheet applied to the entire window. The prompt manager
lets you inspect available prompt templates, browse any stored history (files placed in a `.history`
folder next to the template), and emit overrides for the currently-selected sessions. When an override is
applied the session is re-analysed in-place and the metadata banner records the override path.

## Drag and drop

You can drag log files from your file manager straight onto the window. The window accepts local file
URLs in `dragEnterEvent`/`dropEvent` and then reuses `load_log_file` for analysis.

## Integration with the CLI

The GUI consumes the same payload structure emitted by `watchpath parse --output-format=json`. Each
`ProcessedSession` holds the JSON payload along with ready-to-display text and Markdown reports, so the
CLI and GUI stay consistent for automation, reporting, and UI usage alike. Switching between the two
interfaces is largely a matter of preference.
