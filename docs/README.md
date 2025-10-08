<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1e3c72,100:2a5298&height=180&section=header&text=🔍%20Watchpath%20Log-Analyst&fontSize=36&fontColor=fff&animation=fadeIn&fontAlignY=38"/>
</p>

<p align="center">
  <b>LLM-powered log parser with anomaly flags 🧠💡</b><br>
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
````

### 2️⃣ Installatie

```bash
git clone https://github.com/<jouw-username>/watchpath-log-analyst.git
cd watchpath-log-analyst
pip install -r requirements.txt
```

### 3️⃣ Start CLI

```bash
python -m watchpath parse ./logs/nginx.log --model mistral
```

De CLI toont vervolgens een scorecard met:

* ⚠️ anomalie-score per sessie
* 🧠 korte LLM-analyse (“analyst note”)
* 📊 statistische context (gemiddelde sessieduur, IP-verspreiding, enz.)

---

## 📸 Voorbeeld-output

```text
[session: 10.0.3.41]
Anomaly Score: 0.91 ⚠️
Analyst Note (LLM):
> Multiple failed auth attempts from a single IP within 3 min window.
> Likely brute-force behavior. Consider temporary block.
```

---

## 🔍 Roadmap

* [ ] YAML/JSON ingest uitbreiden
* [ ] Grafana-export plugin
* [ ] Fine-tuning via lokale embeddings
* [ ] Real-time API stream
* [ ] Auto-correlation tussen sessies

---

## 🧑‍💻 Contributie

Pull requests en feature-suggesties zijn welkom!
Gebruik bij voorkeur **feature branches** en voeg duidelijke testcases toe.

```bash
git checkout -b feature/<naam>
```

---

## 🧠 Licentie

Released onder de **MIT-licentie**.
Gebruik het, wijzig het, deel het — zolang de credits behouden blijven.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:2a5298,100:1e3c72&height=120&section=footer"/>
</p>

<p align="center">
  <a href="https://github.com/"NookiDooki">
    <img src="https://img.shields.io/github/stars/NookiDooki/Watchpath?style=social" />
  </a>
  <a href="https://ollama.com">
    <img src="https://img.shields.io/badge/Ollama-local--LLM-blue?logo=openai" />
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Made%20with-Python%20🐍-green?logo=python" />
  </a>
</p>
```
