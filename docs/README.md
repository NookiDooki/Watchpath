<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1e3c72,100:2a5298&height=180&section=header&text=🔍%20Watchpath%20Log-Analyst&fontSize=36&fontColor=fff&animation=fadeIn&fontAlignY=38"/>
</p>

<p align="center">
  <b>LLM-powered log parser with anomaly flags by ABI-Research 🧠💡</b><br>
  <em>From raw logs → structured sessions → statistical anomalies → AI-written analyst notes</em>
</p>

---

## 🚀 Overzicht

**Watchpath Log-Analyst** is een open-source tool voor automatische loganalyse met AI-ondersteuning.  
Het parseert ruwe logs (zoals `nginx` of `auth`), extraheert kenmerken per sessie/IP, detecteert afwijkingen met eenvoudige regels & statistiek,  
en laat vervolgens een **lokale LLM** (via [Ollama](https://ollama.com)) een korte _“analyst note”_ schrijven voor elke verdachte sessie.

### 🧭 Waarom dit project?

- 🔐 **Privacy-vriendelijk** — volledig lokaal via Ollama (geen cloud-LLM’s)  
- 🤖 **AI + Security** — combineert traditionele analyse met LLM-context  
- ⚡ **Demo-klaar in 2–3 dagen** — scorecards, anomaly flags en menselijke leesbare samenvattingen  
- 💬 **Open-source mindset** — transparant, uitbreidbaar en reproduceerbaar  

---

## 🧩 Stack

| Domein | Technologie |
|:--|:--|
| **Core** | Python 3.11+, Typer + Rich (CLI), FastAPI (API) |
| **AI-laag** | Ollama + Mistral 7B Instruct *(of Llama 3.x Instruct)* |
| **Analytics** | Numpy / Scipy / Pandas (feature-extractie & statistiek) |
| **Output** | CLI + web endpoint met JSON/Markdown “analyst notes” |

---

## ⚙️ Quickstart

### 1️⃣ Vereisten

- Python 3.11 of hoger  
- [Ollama](https://ollama.com) geïnstalleerd en actief  
- Model ophalen:

```bash
ollama pull mistral
# of
ollama pull llama3.1
