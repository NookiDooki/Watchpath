# Watchpath CLI Guide

The Watchpath command-line interface exposes the log analysis pipeline used throughout the project.
It lets you parse access logs into visitor sessions, send those sessions to an Ollama large language
model, and render structured anomaly reports. The CLI lives in [`watchpath/cli.py`](../src/watchpath/cli.py)
and is accessible either through the `watchpath` console script (if installed) or by running
`python -m watchpath` directly.

> 🌸 **Need visuals or quick starts?** Visit the [main README](README.md) for animated headers, quick
> install steps, and cross-links to the rest of the docs family.

## Commands

Watchpath provides two subcommands: `parse` for terminal-based analysis and `gui` for launching the
desktop experience.

### `watchpath parse`

`watchpath parse` ingests a log file, groups records into sessions, calls Ollama for anomaly scoring,
and writes the resulting reports to standard output.

```
watchpath parse <log_path> [options]
```

**Arguments**

| Option | Description |
| --- | --- |
| `log_path` | Path to the access log file to analyze. Required. |
| `--model` | Ollama model name. Defaults to `mistral:7b-instruct`. |
| `--chunk-size` | Maximum number of log lines from a session sent to the model. Defaults to `50`. |
| `--prompt` | Path to the base prompt template passed to the model. Defaults to `prompts/base_prompt.txt`. |
| `--output-format` | Report format: `text`, `markdown`, or `json`. Defaults to `text`. |
| `--rich` | When set with `--output-format=text`, renders styled panels using [Rich](https://rich.readthedocs.io). |
| `--confirm-each-session` | Prompts after every session before continuing, useful for interactive triage. |

Under the hood the command:

1. Validates the log file and prompt template.
2. Parses sessions with [`watchpath.parser.load_sessions`](../src/watchpath/parser.py) and summarises them with `summarize_sessions`.
3. For each session, builds a log chunk via `build_session_chunk` and sends it to
   [`watchpath.ai.analyze_logs_ollama_chunk`](../src/watchpath/ai.py).
4. Combines structured and AI output into reports using `format_session_report` or
   `format_session_markdown`, or emits the raw payload as JSON.

Because the CLI uses the Ollama command-line tool, ensure the `ollama` executable is available on
`PATH`. If the executable is missing or a model fails to load the command raises a descriptive
error.

**Examples**

```bash
# Render human-readable text reports
watchpath parse logs/example.log --output-format=text

# Create Markdown for documentation or ticketing systems
watchpath parse logs/example.log --output-format=markdown > findings.md

# Produce JSON for downstream automation
watchpath parse logs/example.log --output-format=json | jq '.[] | {session_id, anomaly_score}'

# Step through the first few sessions manually
watchpath parse logs/example.log --confirm-each-session
```

`watchpath parse` caps the analysis to the first five sessions by default (`DEFAULT_SESSION_LIMIT`).
Use `--confirm-each-session` together with targeted log files when you need to prioritise specific
traffic. For richer recipes and automation patterns, jump to [Usage recipes](usage.md).

### `watchpath gui`

`watchpath gui` provides a convenience shortcut for starting the Qt-based interface described in the
[GUI guide](gui.md). It accepts a subset of the parse options and mirrors the CLI defaults so both
experiences stay aligned:

| Option | Description |
| --- | --- |
| `log_path` | Optional log file preloaded when the window opens. |
| `--model` | Default Ollama model shown in the UI model picker. |
| `--chunk-size` | Initial log chunk size fed into the model. |
| `--prompt` | Prompt template path shared with the CLI. |

The command passes the resolved options to [`watchpath.gui.launch_gui`](../src/watchpath/gui/__init__.py),
which spins up the Qt event loop, creates the main window, and (if provided) schedules the log to load
once the UI is ready. Any file browsing or theme adjustments happen inside the GUI itself.

## Exit codes

Both subcommands return `0` on success. Errors such as missing files, invalid prompt templates, or
Ollama failures surface as exceptions, resulting in a non-zero exit code suitable for shell scripting.

## Integrating with other tools

The JSON output produced by `watchpath parse --output-format=json` mirrors the payload consumed by the
GUI (`ProcessedSession.payload`). It contains anomaly scores, analyst notes, evidence snippets, and
session/global metrics, making it a good fit for automation, dashboards, or alerting workflows.

## Troubleshooting

- **`FileNotFoundError: Log file not found`** — Verify the path passed to `log_path`.
- **`Prompt template not found`** — Double check the `--prompt` path; the default prompt lives under
  `prompts/base_prompt.txt` in the repository root.
- **`Ollama executable not found`** — Install [Ollama](https://ollama.ai) locally and ensure the binary
  is on `PATH`.
- **Analysis stops early** — If you enabled `--confirm-each-session` and declined to continue, the CLI
  reports "Analysis stopped early" and exits cleanly after printing the reports collected so far.
