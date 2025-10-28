"""FastAPI application exposing Watchpath analysis endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .ai import analyze_logs_ollama_chunk
from .parser import (
    build_session_chunk,
    build_session_payload,
    format_session_markdown,
    format_session_report,
    load_sessions,
    summarize_sessions,
)

DEFAULT_PROMPT_PATH = Path("prompts/base_prompt.txt")

AnalyzerFn = Callable[[str, str, str, str], Any]


class ParseRequest(BaseModel):
    """Request payload for the ``/parse`` endpoint."""

    log_path: str
    model: str = "mistral:7b-instruct"
    chunk_size: int = 50
    prompt_path: str | None = None
    include_text: bool = False
    include_markdown: bool = True


app = FastAPI(title="Watchpath API", version="0.2.0")

_analyzer: AnalyzerFn = analyze_logs_ollama_chunk


def set_analyzer(func: AnalyzerFn) -> None:
    """Override the analyzer callable. Primarily used for tests."""

    global _analyzer
    _analyzer = func


@app.post("/parse")
def parse_logs(request: ParseRequest) -> dict[str, Any]:
    """Parse a log file and return structured session analysis."""

    log_path = Path(request.log_path)
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Log file not found: {log_path}")

    if request.chunk_size <= 0:
        raise HTTPException(status_code=400, detail="chunk_size must be positive")

    prompt_path = Path(request.prompt_path) if request.prompt_path else DEFAULT_PROMPT_PATH
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail=f"Prompt template not found: {prompt_path}")

    sessions = load_sessions(str(log_path))
    stats = summarize_sessions(sessions)

    global_stats = {
        "mean_session_duration_seconds": stats.mean_session_duration,
        "ip_distribution": stats.ip_distribution,
        "request_counts": stats.request_counts,
        "top_ips": sorted(stats.ip_distribution.items(), key=lambda item: item[1], reverse=True)[:3],
    }

    if not sessions:
        return {"sessions": [], "global_stats": global_stats}

    responses = []
    for session in sessions:
        chunk_text = build_session_chunk(session, request.chunk_size)
        analysis = _analyzer(
            session_id=session.session_id,
            log_chunk=chunk_text,
            prompt_path=str(prompt_path),
            model=request.model,
        )

        payload = build_session_payload(session, analysis, stats)
        formats: dict[str, str] = {}
        if request.include_text:
            formats["text"] = format_session_report(session, analysis, stats)
        if request.include_markdown:
            formats["markdown"] = format_session_markdown(session, analysis, stats)
        if formats:
            payload["formats"] = formats

        responses.append(payload)

    return {"sessions": responses, "global_stats": global_stats}


__all__ = ["app", "set_analyzer"]
