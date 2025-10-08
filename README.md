# Watchpath log-analyst (OSS) — LLM-powered log parser with anomaly flags

**Doel:** Ruwe logs (bijv. nginx, auth) automatisch parsen → features per sessie/IP → simpele anomaly-detectie (regels + statistiek) → een **lokale** LLM (Ollama + Mistral) schrijft een korte “analyst note” per verdachte sessie.

**Waarom dit project?**
- Sluit aan op AI+Security: *“LLM-powered log parser with anomaly detection”*
- 100% open-source, privacy-vriendelijk (LLM lokaal via Ollama)
- Demo-baar in 2–3 dagen: duidelijke scorecards + analyst notes

## Stack
- Python, Typer/Rich (CLI), FastAPI (API)
- Ollama + Mistral 7B Instruct (of Llama 3.* Instruct)
- Numpy/Scipy/Pandas voor features & statistiek

## Quickstart

### 1) Vereisten
- Python 3.11+
- [Ollama](https://ollama.com) geïnstalleerd en draaiend
- Model ophalen:
  ```bash
  ollama pull mistral
  # of: ollama pull llama3.1
