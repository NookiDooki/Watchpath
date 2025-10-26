from pathlib import Path
import subprocess
from typing import Optional


def analyze_logs_ollama_chunk(
    log_chunk: str,
    prompt_path: str,
    model: str = "mistral:7b-instruct",
    chart_context: Optional[str] = None,
    summary_context: Optional[str] = None,
):
    """
    Analyze a chunk of logs directly using a local Ollama model.
    Returns the AI output (line-by-line classification).
    """
    base_prompt = Path(prompt_path).read_text()

    context_sections = []
    if summary_context:
        context_sections.append("### ANALYTICS SNAPSHOT ###\n" + summary_context.strip())
    if chart_context:
        context_sections.append("### CHART INVENTORY ###\n" + chart_context.strip())

    context_block = "\n\n".join(context_sections)
    if context_block:
        context_block += "\n\n"

    full_prompt = (
        f"{base_prompt}\n\n{context_block}### TASK ###\nAnalyze the following logs:\n{log_chunk}\n"
    )

    result = subprocess.run(
        ["ollama", "run", model],
        input=full_prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        raise RuntimeError(f"Ollama failed: {result.stderr.decode()}")

    return result.stdout.decode().strip()


def chunk_log_file(log_path: str, chunk_size=50):
    """
    Yield chunks of log lines as strings from a log file.
    """
    lines = Path(log_path).read_text().splitlines()
    for i in range(0, len(lines), chunk_size):
        yield "\n".join(lines[i:i+chunk_size])
