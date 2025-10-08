<p align="center">
  <img src="./A_digital_graphic_design_banner_for_the_Watchpath.png" width="100%" alt="Watchpath Log-Analyst Banner"/>
</p>

<p align="center">
  <h2>🔍 Watchpath Log-Analyst</h2>
  <em>LLM-powered log parser with anomaly flags — an <b>ABI Research</b> project</em>
</p>

---

## 🚀 Overzicht

**Watchpath Log-Analyst** is een open-source Python-tool voor automatische loganalyse met lokale AI-ondersteuning.  
De applicatie parseert ruwe logs (zoals `nginx` of `auth`), groepeert data per sessie/IP,  
detecteert afwijkingen via regels en statistiek, en laat een **lokale LLM** (via [Ollama](https://ollama.com))  
een korte _“analyst note”_ schrijven voor verdachte gebeurtenissen.

> _Een combinatie van klassieke analyse, moderne AI-context en volledige privacy._

---

## 🧭 Kernprincipes

- 🔐 **Privacy First** — 100% lokaal, geen cloud-LLM of data-exfiltratie.  
- ⚙️ **Explainable AI** — Uitlegbaar, toetsbaar en herleidbaar.  
- 🧠 **Efficiënt en schaalbaar** — Snelle setup, uitbreidbaar naar meerdere logtypes.  
- 🤝 **Ontwikkeld door ABI Research** —  
  _Ilyes Lallam (Lead) · Asil · Bilal._

---

## 🧩 Stack

| Domein | Technologie | Functie |
|:--|:--|:--|
| **Core** | Python 3.11+, Typer + Rich | CLI-interface |
| **Backend** | FastAPI | REST-API voor integratie |
| **AI-laag** | Ollama + Mistral 7B / Llama 3.x | Lokale LLM-analyse |
| **Analyse** | NumPy · SciPy · Pandas | Feature-extractie & statistiek |
| **Output** | Markdown · JSON | Analyst Notes & Scorecards |

---

## ⚙️ Quickstart

### 1️⃣ Vereisten

```bash
python3 --version  # 3.11+
ollama serve       # start lokale LLM-service
ollama pull mistral
# of: ollama pull llama3.1
````

### 2️⃣ Installatie

```bash
git clone https://github.com/<jouw-username>/watchpath-log-analyst.git
cd watchpath-log-analyst
pip install -r requirements.txt
```

### 3️⃣ Gebruik

```bash
python -m watchpath parse ./logs/nginx.log --model mistral
```

De CLI toont:

* ⚠️ **Anomalie-score** per sessie
* 🧠 **LLM-gegenereerde analyst note**
* 📊 **Feature-statistieken** (sessieduur, IP-distributie, trends)

---

## 📸 Voorbeeld-output

```text
[session: 10.0.3.41]
Anomaly Score: 0.91 ⚠️
Analyst Note (LLM):
> Multiple failed auth attempts from a single IP within 3-minute window.  
> Likely brute-force behavior. Consider temporary block.
```

---

## 🧭 Roadmap

* [ ] YAML/JSON-ingest uitbreiden
* [ ] Grafana-export & dashboards
* [ ] Fine-tuning via lokale embeddings
* [ ] Realtime API-stream
* [ ] Cross-session correlatie

---

## 🤝 Contributie

Pull requests en feature-suggesties zijn welkom!
Gebruik **feature branches** en voeg testcases toe.

```bash
git checkout -b feature/<naam>
```

> *Samen bouwen we een uitlegbare AI-tooling-stack voor cybersecurity.*

---

## 🧠 Licentie

Released onder de **MIT-licentie**.
Vrij gebruik, wijziging en distributie toegestaan met bronvermelding:

**© ABI Research — Ilyes Lallam (Lead) · Asil · Bilal**

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:2a5298,100:1e3c72&height=100&section=footer"/>
</p>

<p align="center">
  <a href="https://github.com/<jouw-username>">
    <img src="https://img.shields.io/github/stars/<jouw-username>/watchpath-log-analyst?style=social" />
  </a>
  <a href="https://ollama.com">
    <img src="https://img.shields.io/badge/Ollama-local--LLM-blue?logo=openai" />
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Made%20with-Python%20🐍-green?logo=python" />
  </a>
</p>
