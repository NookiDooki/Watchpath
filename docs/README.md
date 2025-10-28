<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=180&text=Watchpath%20Observatory&fontSize=42&color=0:1d2671,100:c33764&fontColor=ffffff" alt="Watchpath Observatory" />
</p>

<p align="center">
  <strong>From raw web logs to story-driven security intelligence.</strong><br/>
  <em>Parse sessions, score anomalies, and brief stakeholders through a kawaii-ready desktop or the classic CLI.</em>
</p>

---

## ✨ Why Watchpath?

* 🧠 **Hybrid analytics** – deterministic statistics surface outliers while a local Ollama model narrates analyst notes for each session.
* 🗂️ **Session-first view** – logs are grouped per visitor with rich metadata (methods, paths, duration, IP).
* 💻 **Dual experience** – choose a fast terminal workflow or explore results inside the pastel "Mochi Observatory" GUI.
* 🔐 **Fully local** – bring your own Ollama model and keep sensitive traffic inside your perimeter.

---

## 🚀 Quickstart

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Pull an Ollama model

```bash
ollama pull mistral:7b-instruct
# or experiment with llama3.1, phi3, etc.
```

### 3. Acquire logs

Drop your access log (NGINX, Apache, auth, custom JSON) into `./logs/`. A sample dataset lives in that folder for experimentation.

---

## 🛠️ Command Line Flow

The CLI keeps you productive when you want quick answers or need to automate reports.

```bash
python -m watchpath parse ./logs/sample.log \
  --model mistral:7b-instruct \
  --chunk-size 60 \
  --prompt prompts/base_prompt.txt \
  --output-format markdown
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

## 🧭 Typical Workflow

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

