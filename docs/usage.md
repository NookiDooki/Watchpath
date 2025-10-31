# Watchpath Usage Recipes

The Watchpath package exposes a CLI that helps analyze access logs and report on suspicious sessions. After installing dependencies (see the [main README](README.md) for quick-start commands), you can run the parser from the project root:

```bash
python -m watchpath parse logs/apache_access_20250302.log --prompt prompts/base_prompt.txt --model mistral:7b-instruct
```

### Alternate Formats

The CLI now supports multiple output formats and optional Rich rendering:

```bash
# Emit Markdown for piping into a renderer
python -m watchpath parse logs/apache.log --output-format markdown > report.md

# Emit JSON for dashboards or the FastAPI endpoint
python -m watchpath parse logs/apache.log --output-format json

# Render colourised panels in the terminal
python -m watchpath parse logs/apache.log --rich
```

## Sample Output

```
Session 192.168.1.14-maria-1 (IP: 192.168.1.14, User: maria)
⚠️ Anomaly Score: 0.82
🧠 Analyst Note: Unusual API enumeration detected with elevated error responses.
📊 Session Statistics:
  • Duration: 0:07:32
  • Requests: 18
  • Unique Paths: 9
  • Methods: GET (16), POST (2)
📊 Global Statistics:
  • Mean Session Duration: 0:04:03
  • Top IPs: 192.168.1.10: 6, 192.168.1.14: 4, 192.168.1.12: 3
  • Request Distribution: GET: 53, POST: 7, PUT: 2
  • Evidence: /api/v1/users?page=3, /api/v1/users?page=4, /api/v1/users?page=5
```

The icons make it easy to identify important parts of the report at a glance:

- ⚠️ **Anomaly Score** — numeric risk indicator between 0 and 1.
- 🧠 **Analyst Note** — short AI-generated summary of suspicious behavior.
- 📊 **Session & Global Statistics** — contextual metrics for the current session and the whole dataset.

Use `--chunk-size` to limit how many log lines from each session are sent to the model, and `--prompt` to supply an alternate prompt template. The [CLI guide](cli.md) details each flag, while the [GUI guide](gui.md) explains how the desktop app mirrors the same payloads.

## FastAPI Endpoint

Run the FastAPI service (for example with `uvicorn watchpath.api:app --reload`) and call the `/parse` endpoint to obtain JSON and Markdown payloads for your GUI:

```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{
        "log_path": "logs/apache_access_20250302.log",
        "chunk_size": 20,
        "include_text": true,
        "include_markdown": true
      }'
```

The response contains structured session data alongside optional text/Markdown renderings, making it simple to drop analyst notes into dashboards or web views. Pair this with the [overview](overview.md) document for a deeper look at data flow.
