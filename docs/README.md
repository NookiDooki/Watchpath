<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=180&text=Watchpath%20Observatory&fontSize=42&color=0:1d2671,100:c33764&fontColor=ffffff" alt="Watchpath Observatory" />
</p>

<p align="center">
  <strong>From raw web logs to story-driven security intelligence.</strong><br/>
  <em>Parse sessions, score anomalies, and brief stakeholders through a kawaii-ready desktop or the classic CLI.</em>
</p>

<p align="center">
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python badge" /></a>
  <a href="#-architecture-snapshot"><img src="https://img.shields.io/badge/architecture-session%20centric-8A2BE2?style=for-the-badge" alt="Architecture badge" /></a>
  <a href="#-cli-playbook"><img src="https://img.shields.io/badge/interface-cli%20%26%20gui-FF69B4?style=for-the-badge" alt="Interface badge" /></a>
</p>

---

## 🧭 Table of Contents

- [✨ Why Watchpath?](#-why-watchpath)
- [🏗️ Architecture Snapshot](#%EF%B8%8F-architecture-snapshot)
- [🚀 Install & Run (Mac and Windows)](#-install--run-mac-and-windows)
- [🛠️ CLI Playbook](#%EF%B8%8F-cli-playbook)
- [🌸 Mochi Observatory GUI](#-mochi-observatory-gui)
- [🗺️ Typical Workflow](#%EF%B8%8F-typical-workflow)
- [📚 Helpful References](#-helpful-references)
- [🤝 Contributing](#-contributing)

---

## ✨ Why Watchpath?

* 🧠 **Hybrid analytics** – deterministic statistics surface outliers while a local Ollama model narrates analyst notes for each session.
* 🗂️ **Session-first view** – logs are grouped per visitor with rich metadata (methods, paths, duration, IP).
* 💻 **Dual experience** – choose a fast terminal workflow or explore results inside the pastel "Mochi Observatory" GUI.
* 🔐 **Fully local** – bring your own Ollama model and keep sensitive traffic inside your perimeter.
* 🧪 **Test harness included** – regression fixtures and prompts ship with the repo so you can reason about results and extend them safely.

---

## 🏗️ Architecture Snapshot

| Layer | Key Modules | Purpose |
| --- | --- | --- |
| **Ingest** | [`src/watchpath/parser.py`](../src/watchpath/parser.py), [`src/watchpath/log_sources/`](../src/watchpath/log_sources) | Tokenises heterogeneous logs and assembles time-bounded visitor sessions. |
| **Analysis** | [`src/watchpath/analyzers/anomaly.py`](../src/watchpath/analyzers/anomaly.py), [`src/watchpath/metrics.py`](../src/watchpath/metrics.py) | Scores each session with statistical heuristics and contextual metrics. |
| **Narration** | [`src/watchpath/llm/ollama_client.py`](../src/watchpath/llm/ollama_client.py), [`prompts/base_prompt.txt`](../prompts/base_prompt.txt) | Sends curated session chunks to an Ollama-hosted model for analyst-ready commentary. |
| **Interfaces** | [`src/watchpath/cli.py`](../src/watchpath/cli.py), [`src/watchpath/gui/app.py`](../src/watchpath/gui/app.py) | Serve results either in Rich-powered terminals or the PySide6 "Mochi Observatory" desktop. |
| **Reports** | [`reports/`](../reports), [`tests/fixtures/`](../tests/fixtures) | Markdown/JSON exports and sample data to validate changes. |

> Tip: The data model emitted by `parser.py` is the contract between the CLI, GUI, and LLM narrator—extend it thoughtfully and add fixtures when you adjust fields.

---

## 🚀 Install & Run (Mac and Windows)

This repo ships without external services; all you need is Python 3.9+ and optionally Ollama for LLM-powered notes.

### 🍎 macOS (Terminal or iTerm2)

```bash
# Install Python 3.9 if it is not already available
brew install python@3.9

# Create and activate an isolated environment
python3.9 -m venv .venv
source .venv/bin/activate

# Pull Python dependencies and (optionally) an Ollama model
pip install -r requirements.txt
ollama pull mistral:7b-instruct  # optional but recommended

# Run the CLI on the sample NGINX log
python -m watchpath parse ./logs/nginx/sample.log

# Launch the GUI with the same log (omit the path to drag-and-drop later)
python -m watchpath gui ./logs/nginx/sample.log
```

### 🪟 Windows 10/11 (PowerShell)

```powershell
# Install Python 3.9 from the Microsoft Store or python.org first
py -3.9 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# (Optional) Pull an Ollama model from WSL or another host
# ollama pull mistral:7b-instruct

# Run the CLI parser
python -m watchpath parse .\logs\nginx\sample.log

# Launch the GUI
python -m watchpath gui .\logs\nginx\sample.log
```

> ✅ **Heads up for Windows users:** The PySide6 GUI requires a desktop session. If you are inside WSL, launch with `python -m watchpath gui` from Windows Python instead of WSL Python.

---

## 🛠️ CLI Playbook

The CLI keeps you productive when you want quick answers or need to automate reports.

```bash
python -m watchpath parse ./logs/sample.log \
  --model mistral:7b-instruct \
  --chunk-size 60 \
  --prompt prompts/base_prompt.txt \
  --output-format markdown \
  --rich
```

### Core options

| Flag | Description |
| --- | --- |
| `log_path` | Path to the log file that should be analyzed. |
| `--model` | Ollama model name. Defaults to `mistral:7b-instruct`. |
| `--chunk-size` | Number of log lines sent per LLM request. |
| `--prompt` | Prompt template passed to the model. |
| `--output-format` | `text`, `markdown`, or `json`. |
| `--rich` | Render a pastel-rich terminal dashboard using Rich panels. |
| `--confirm-each-session` | Pause after every session so you can stop early. |

### What you receive

* ⚠️ **Anomaly score** – probability that the session is suspicious.
* 🧠 **Analyst note** – a concise Ollama-generated summary.
* 📊 **Context** – method counts, path diversity, session length, IP metadata.
* 🗒️ **Markdown or JSON** – feed straight into reports, dashboards, or docs.

> Tip: use `jq` together with `--output-format json` to automate triage playbooks.

---

## 🌸 Mochi Observatory GUI

Prefer a kawaii command center? Launch the PySide6 desktop experience:

```bash
python -m watchpath gui ./logs/sample.log \
  --model mistral:7b-instruct \
  --chunk-size 60 \
  --prompt prompts/base_prompt.txt
```

### Highlights

* 🎠 **Session carousel** – swipe through visitor journeys with animated anomaly rings.
* 💬 **Evidence storybook** – collapse/expand AI evidence, raw log lines, and timeline views.
* 🧁 **Drag & drop ingest** – drop new logs onto the window to trigger fresh analysis.
* 🌈 **Real-time vibes** – background threads stream results while pastel mascots react to risk levels.

You can launch the GUI without a log path and drag files in later. Settings panels let you adjust model name, chunk size, and prompts on the fly.

---

## 🗺️ Typical Workflow

1. **Collect** – ingest your log file (CLI argument or drag-and-drop).
2. **Process** – Watchpath groups lines into sessions and applies anomaly scoring.
3. **Review** – read analyst notes, inspect evidence, and compare sessions side-by-side.
4. **Act** – export Markdown/JSON from the CLI or copy notes from the GUI for incident tickets.

---

## 📚 Helpful References

* `prompts/base_prompt.txt` – the default LLM system prompt. Customize it to reflect your playbook.
* `tests/fixtures/` – sample logs and expected payloads, handy for understanding the session schema.
* `src/watchpath/parser.py` – deep dive into how sessions are assembled and scored.

---

## 🤝 Contributing

We welcome pull requests! Please include tests (`pytest`) and share screenshots or recordings for UI changes so others can preview the kawaii flair.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer&color=0:c33764,100:1d2671" alt="Watchpath footer" />
</p>
