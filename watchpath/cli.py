"""Command line interface for Watchpath."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .analysis import OllamaError, analyze_log_file

app = typer.Typer(add_completion=False, help="AI-assisted log analysis toolkit")
console = Console()


def _validate_chunk_size(_: typer.Context, param: typer.CallbackParam, value: int) -> int:
    if value <= 0:
        raise typer.BadParameter("Chunk size must be greater than zero.")
    return value


@app.command("analyze")
def analyze_command(
    log_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to the log file to analyze."),
    prompt_file: Path = typer.Option(
        Path("prompts/anomaly_prompt.txt"),
        "--prompt-file",
        "-p",
        help="Prompt template used to guide the LLM.",
    ),
    model: str = typer.Option("mistral:7b-instruct", "--model", "-m", help="Ollama model to execute."),
    report_file: Optional[Path] = typer.Option(
        None,
        "--report-file",
        "-o",
        help="Optional path to store the Markdown report.",
    ),
    chunk_size: int = typer.Option(50, "--chunk-size", "-c", callback=_validate_chunk_size, help="Number of log lines per chunk."),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Timeout (in seconds) for each Ollama request.",
    ),
) -> None:
    """Analyze *log_file* and optionally persist the generated report."""

    if prompt_file and not prompt_file.exists():
        raise typer.BadParameter(f"Prompt file not found: {prompt_file}", param_hint="--prompt-file")

    results = []
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(bar_width=None),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Analyzing log chunks", total=None, start=False)
            progress.start_task(task_id)

            for chunk_result in analyze_log_file(
                log_file,
                prompt_file,
                model=model,
                chunk_size=chunk_size,
                timeout=timeout,
            ):
                results.append(chunk_result)
                progress.advance(task_id)

    except OllamaError as exc:
        console.print(f"[bold red]Failed to analyze logs:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    report = "\n\n".join(results)

    if report_file is not None:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(report, encoding="utf-8")
        console.print(Panel.fit(f"Report written to [bold]{report_file}[/bold]", title="Success"))
    else:
        console.print(Panel.fit(report or "No output generated", title="Analysis Report"))


def main() -> None:
    app()


app.command("parse")(analyze_command)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
