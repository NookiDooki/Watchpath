```python
import typer
from rich import print
from pathlib import Path
from src.parser import parse_logs
from src.features import build_sessions
from src.anomaly import flag_anomalies
from src.llm_notes import add_llm_notes
from datetime import datetime

app = typer.Typer(help="log-analyst CLI")

@app.command()
def run(
    nginx: Path = typer.Option(None, help="Path to nginx log"),
    auth: Path  = typer.Option(None, help="Path to auth log"),
    model: str  = typer.Option("mistral", help="Ollama model name"),
    out: Path   = typer.Option(Path("reports/report.md"), help="Markdown report output")
):
    # 1) parse
    events = []
    if nginx:
        events += parse_logs("nginx", nginx.read_text())
    if auth:
        events += parse_logs("auth", auth.read_text())
    print(f"[bold cyan]Parsed events:[/bold cyan] {len(events)}")

    # 2) features -> grouped sessions
    sessions = build_sessions(events)
    print(f"[bold cyan]Sessions built:[/bold cyan] {len(sessions)}")

    # 3) anomaly flags
    suspicious = flag_anomalies(sessions)
    print(f"[bold yellow]Suspicious sessions:[/bold yellow] {len(suspicious)}")

    # 4) LLM analyst notes (local Ollama)
    suspicious = add_llm_notes(suspicious, model=model)

    # 5) render markdown report
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write(f"# log-analyst report — {datetime.utcnow().isoformat()}Z\n\n")
        f.write(f"Parsed events: {len(events)}\n\n")
        f.write(f"Suspicious sessions: {len(suspicious)}\n\n")
        for s in suspicious[:25]:
            f.write(f"## Session {s['id']}\n\n")
            f.write(f"- src_ip: {s.get('src_ip_anon')}\n")
            f.write(f"- count: {s.get('req_count')}, fail_ratio: {s.get('fail_ratio'):.2f}\n")
            f.write(f"- rules: {', '.join(s.get('rules_triggered', [])) or '—'}\n")
            f.write(f"- stats_flags: {', '.join(s.get('stats_flags', [])) or '—'}\n")
            f.write(f"- paths_sample: {', '.join(s.get('paths_sample', [])[:5])}\n\n")
            note = s.get("llm_note", "").strip()
            if note:
                f.write(f"**Analyst note (LLM):**\n\n> {note}\n\n")
            f.write("---\n\n")
    print(f"[green]Report written to {out}[/green]")

if __name__ == "__main__":
    app()