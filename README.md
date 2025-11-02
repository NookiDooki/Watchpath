<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=180&text=Watchpath%20+Mochi%20Observatory&fontSize=42&color=0:1d2671,100:c33764&fontColor=ffffff" alt="Watchpath Observatory" />
</p>

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=500&size=22&pause=1500&color=C33764&center=true&vCenter=true&width=602&lines=from+raw+access+logs+to+incident+briefings;Dual+CLI+%26+PySide6+workflows;LLM+notes+without+leaving+your+perimeter" alt="Animated Watchpath tagline" />
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python badge" /></a>
  <a href="#-documentation-portal"><img src="https://img.shields.io/badge/docs-portal-8A2BE2?style=for-the-badge&logo=read-the-docs&logoColor=white" alt="Docs badge" /></a>
  <a href="#-feature-highlight"><img src="https://img.shields.io/badge/interface-cli%20%26%20gui-FF69B4?style=for-the-badge" alt="Interface badge" /></a>
</p>

<p align="center">
  <a href="#-quick-start"><b>Quick start</b></a> ·
  <a href="#-feature-highlight"><b>Features</b></a> ·
  <a href="#-mochi-workflows"><b>Workflows</b></a> ·
  <a href="#-documentation-portal"><b>Documentation</b></a>
</p>

---

## 🧭 Table of Contents

- [✨ Why Watchpath?](#-why-watchpath)
- [🌟 Feature Highlight](#-feature-highlight)
- [🚀 Quick Start (CLI & GUI)](#-quick-start)
- [🏗️ Architecture Snapshot](#%EF%B8%8F-architecture-snapshot)
- [🍡 Mochi Workflows](#-mochi-workflows)
- [📘 Documentation Portal](#-documentation-portal)
- [📚 Helpful References](#-helpful-references)
- [🤝 Contributing](#-contributing)

---

## ✨ Why Watchpath?

<div align="center">
  <table>
    <tr>
      <td align="left">🧠 <strong>Hybrid analytics</strong><br/><em>Deterministic statistics meet LLM narration so every session comes with context.</em></td>
      <td align="left">💻 <strong>Dual experience</strong><br/><em>Choose between an automation-friendly CLI or the "Mochi Observatory" GUI.</em></td>
    </tr>
    <tr>
      <td align="left">🔐 <strong>Local by design</strong><br/><em>Bring your own Ollama model and keep sensitive traffic within your perimeter.</em></td>
      <td align="left">🧪 <strong>Regression friendly</strong><br/><em>Curated fixtures, prompts, and reports make extending the pipeline predictable.</em></td>
    </tr>
  </table>
</div>

---

## 🌟 Feature Highlight

> Watchpath distils noisy access logs into stories your incident responders can act on.

- 🎛️ **Session-centric parsing** – `parser.py` groups Apache/Nginx logs into rich `Session` objects that power every interface.
- 🧾 **Narrated anomaly reports** – `ai.py` wraps Ollama output with heuristics so analysts always see a useful note and evidence.
- 🗺️ **Global telemetry** – sparklines, status histograms, and timeline metrics surface hotspots across the dataset.
- 🧁 **Mochi Observatory GUI** – drag-and-drop logs, prompt overrides, pastel theming, and kaomoji-driven severity states.
- 🧰 **Automation-ready CLI** – Markdown/JSON/text outputs integrate with ticketing systems, dashboards, or scripts.

---

## 🚀 Quick Start

### 🍎 macOS (Terminal or iTerm2)

```bash
brew install python@3.9
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull mistral:7b-instruct  # optional but recommended

# Parse the bundled sample log via the CLI
python -m watchpath parse ./logs/apache_access_20250302.log

# Launch the Mochi Observatory GUI
python -m watchpath gui
```

### 🪟 Windows 10/11 (PowerShell)

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional: ollama pull mistral:7b-instruct

python -m watchpath parse .\logs\apache_access_20250302.log
python -m watchpath gui
```

> 💡 **Tip:** Launch `python -m watchpath gui` without a file to drag-and-drop logs later. The GUI shares defaults with the CLI, so settings stay in sync.

---

## 🏗️ Architecture Snapshot

<details>
<summary>Peek under the hood</summary>

| Layer | Key Modules | Purpose |
| --- | --- | --- |
| **Ingest** | [`src/watchpath/parser.py`](src/watchpath/parser.py) | Tokenises heterogeneous logs, groups them into sessions, and computes aggregates. |
| **Analysis** | [`src/watchpath/ai.py`](src/watchpath/ai.py), [`src/watchpath/metrics.py`](src/watchpath/metrics.py) | Scores sessions, enriches LLM output, and normalises evidence. |
| **Interfaces** | [`src/watchpath/cli.py`](src/watchpath/cli.py), [`src/watchpath/gui/main_window.py`](src/watchpath/gui/main_window.py) | Serve reports via Rich-powered terminals or the PySide6 Mochi Observatory. |
| **Reports & Docs** | [`docs/`](docs), [`reports/`](reports) | Living documentation, sample exports, and analysis playbooks. |

</details>

> The CLI and GUI consume the same JSON payload (`build_session_payload`), so automation scripts and desktop analysts always agree on risk, evidence, and metadata.

---

## 🍡 Mochi Workflows

1. **Collect** – ingest a log file via CLI argument or drag-and-drop in the GUI.
2. **Process** – sessions flow through the shared parser and Ollama analysis worker.
3. **Review** – compare kaomoji-driven severity, analyst notes, and evidence side-by-side.
4. **Act** – export Markdown/JSON, copy summaries, or pin sessions for deeper dives.

<details>
<summary>CLI Cheat Sheet</summary>

```bash
python -m watchpath parse ./logs/apache_access_20250302.log \
  --model mistral:7b-instruct \
  --chunk-size 60 \
  --prompt prompts/base_prompt.txt \
  --output-format json
```

</details>

<details>
<summary>GUI Highlights</summary>

- 🎠 **Session carousel** for quick triage with filters and keyboard shortcuts.
- 💬 **Evidence storybook** toggling between analyst notes, logs, and Markdown.
- 📦 **Prompt manager** with live previews and version history.
- 🎨 **Theme switcher** and kaomoji severity cards for instant vibes.

</details>

---

## 📘 Documentation Portal

<table>
  <tr>
    <td align="center">
      <a href="docs/overview.md"><img src="https://img.shields.io/badge/Overview-1d2671?style=for-the-badge&logo=bookstack&logoColor=white" alt="Overview badge"/></a>
      <br/><sub>System map, data flow, and extensibility tips.</sub>
    </td>
    <td align="center">
      <a href="docs/cli.md"><img src="https://img.shields.io/badge/CLI%20Guide-c33764?style=for-the-badge&logo=terminal&logoColor=white" alt="CLI badge"/></a>
      <br/><sub>Flags, automation patterns, and troubleshooting.</sub>
    </td>
    <td align="center">
      <a href="docs/gui.md"><img src="https://img.shields.io/badge/GUI%20Guide-ff8fab?style=for-the-badge&logo=qt&logoColor=white" alt="GUI badge"/></a>
      <br/><sub>Mochi Observatory tour, threading, and UX tips.</sub>
    </td>
    <td align="center">
      <a href="docs/usage.md"><img src="https://img.shields.io/badge/Usage%20Recipes-8A2BE2?style=for-the-badge&logo=markdown&logoColor=white" alt="Usage badge"/></a>
      <br/><sub>Sample commands, API snippets, and export formats.</sub>
    </td>
  </tr>
</table>

---

## 📚 Helpful References

- `prompts/base_prompt.txt` – baseline LLM instructions; duplicate it when crafting incident-specific voices.
- `logs/` – bundled sample datasets for Apache, database, and system activity.
- `reports/` – curated Markdown exports you can adapt for stakeholder briefings.
- [`docs/overview.md`](docs/overview.md) – deep dive into architecture and extensibility patterns.

---

## 🤝 Contributing

We love contributions! Please:

1. Open an issue or discussion for larger ideas.
2. Include tests (`pytest`) or sample logs when altering behaviour.
3. Share screenshots/recordings for UI changes so others can preview the Mochi glow.
4. Respect the vibes—comments and copy should stay playful yet informative.

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer&color=0:c33764,100:1d2671" alt="Watchpath footer" />
</p>
