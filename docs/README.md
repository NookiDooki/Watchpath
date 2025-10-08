<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1e3c72,100:2a5298&height=140&section=header&text=🔍%20Watchpath%20Log-Analyst&fontSize=34&fontColor=fff&animation=fadeIn&fontAlignY=35"/>
</p>

<p align="center">
  <b>AI + Security Research Initiative</b><br>
  <em>From raw logs to explainable anomalies — powered by local LLMs</em>
</p>

---

## 🎯 Doel

**Watchpath Log-Analyst (OSS)** combineert traditionele loganalyse met LLM-gestuurde interpretatie.  
Het project parseert ruwe logs (zoals `nginx` of `auth`), structureert data per sessie/IP,  
detecteert anomalieën via eenvoudige regels & statistiek, en laat een **lokale LLM** (Ollama + Mistral)  
automatisch korte *“analyst notes”* genereren per verdachte sessie.

---

## 🌐 Kernwaarden — De 3 C’s van Watchpath

| C | Kernvraag | Betekenis voor Watchpath |
|:--|:--|:--|
| **Context** | “Wat willen we echt zien?” | Combineert logstructuur en netwerk-gedrag om AI-context te behouden. |
| **Constraints** | “Wat mag of kan niet?” | Draait volledig lokaal (geen cloud-LLM’s, geen data-lekkage). |
| **Criteria** | “Wanneer is iets afwijkend?” | Statistische grenzen + heuristieken maken anomalieën toetsbaar. |

---

## 🧠 Waarom dit project?

- 🔐 **Privacy-vriendelijk:** LLM draait **lokaal** via [Ollama](https://ollama.com)  
- 🧩 **Transparant:** elke beslissing is uitlegbaar — geen black-box AI  
- 🧮 **Meetbaar:** anomaly-score + bronverwijzing + context-fit  
- ⚙️ **Praktisch:** demobaar binnen 2–3 dagen (CLI + API-output)  
- 🧑‍🏫 **Onderzoeksgericht:** ideaal voor labs, CTF-trainingen of onderwijs in AI + Security  

---

## ⚙️ Stack & Architectuur

| Component | Technologie | Functie |
|:--|:--|:--|
| **CLI & API** | Typer + Rich + FastAPI | Interactie & endpoints |
| **AI-laag** | Ollama + Mistral 7B / Llama 3.x | Lokale LLM-analyse |
| **Analysetools** | NumPy / SciPy / Pandas | Feature-extractie & statistiek |
| **Outputvormen** | Markdown, JSON | Analyst Notes + Scorecards |

---

## 🚀 Quickstart

### 1️⃣ Vereisten
```bash
# Python en Ollama voorbereiden
python3 --version  # 3.11+
ollama serve       # start lokale LLM-service
ollama pull mistral
# alternatief: ollama pull llama3.1
````

### 2️⃣ Installatie

```bash
git clone https://github.com/<jouw-username>/watchpath-log-analyst.git
cd watchpath-log-analyst
pip install -r requirements.txt
```

### 3️⃣ Run & Analyse

```bash
python -m watchpath parse ./logs/nginx.log --model mistral
```

➡️ Output bevat:

* **Anomaly-score per sessie**
* **LLM-gegenereerde analyst note**
* **Feature-statistieken** per IP/sessie

---

## 🧾 Voorbeeld-output

```text
[session: 10.0.3.41]
Anomaly Score: 0.91 ⚠️
Analyst Note (LLM):
> Multiple failed auth attempts from a single IP within 3-min window.  
> Likely brute-force behavior. Consider temporary block.
```

---

## 🧭 Roadmap

* [ ] Auto-labeling van anomalieën
* [ ] Grafana-export & live dashboard
* [ ] Embedding-based fine-tuning
* [ ] Cross-session correlatie
* [ ] Integratie met open CTI-feeds

---

## 🤝 Contributie

Open-source is samenwerking.
Fork, test, verbeter — en deel je eigen *analyst modules*.

```bash
git checkout -b feature/<naam>
```

---

## 🧩 Licentie

MIT-licentie — vrij gebruik, aanpassing en distributie
met bronvermelding: *ABI Research / Ilyes Lallam & Asil Elkhaloui.*

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
```

---
### 💬 Toelichting

Deze versie sluit visueel en inhoudelijk aan op je **ABI Research-presentatie**:

* identieke **kleurgradatie** (`#1e3c72 → #2a5298`);
* **research-toon** met focus op AI-eigenaarschap en uitlegbaarheid;
* secties in **slide-stijl** (kort, helder, semantisch);
* **3 C’s-model** geïntegreerd in de kernfilosofie van het project.
