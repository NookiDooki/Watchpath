"""AI integration utilities for Watchpath."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SessionAnalysis:
    """Structured response produced by the language model."""

    session_id: str
    anomaly_score: Optional[float]
    analyst_note: str
    evidence: str | list[str]
    raw_response: str


def analyze_logs_ollama_chunk(
    session_id: str,
    log_chunk: str,
    prompt_path: str,
    model: str = "mistral:7b-instruct",
) -> SessionAnalysis:
    """Analyze a chunk of session logs using an Ollama model."""

    base_prompt = Path(prompt_path).read_text()
    full_prompt = (
        f"{base_prompt}\n\n### TASK ###\n"
        f"Session ID: {session_id}\n"
        "Provide an anomaly score between 0 and 1, a short analyst note, "
        "and highlight any supporting evidence. Respond with JSON containing "
        "`anomaly_score`, `analyst_note`, and optionally `evidence`.\n"
        "Logs:\n"
        f"{log_chunk}\n"
    )

    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=full_prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - depends on runtime environment
        raise RuntimeError("Ollama executable not found. Install Ollama to enable analysis.") from exc

    if result.returncode != 0:
        raise RuntimeError(f"Ollama failed: {result.stderr.decode()}")

    raw_output = result.stdout.decode().strip()
    anomaly_score, analyst_note, evidence = _parse_analysis_output(raw_output)

    return SessionAnalysis(
        session_id=session_id,
        anomaly_score=anomaly_score,
        analyst_note=analyst_note,
        evidence=evidence or log_chunk,
        raw_response=raw_output,
    )


def _parse_analysis_output(output: str) -> tuple[Optional[float], str, Optional[str]]:
    """Extract structured information from a model response."""

    cleaned = output.strip()
    if not cleaned:
        return None, "No analyst note returned.", None

    # Try JSON first
    try:
        data = json.loads(cleaned)
        score = _safe_float(data.get("anomaly_score"))
        note = str(data.get("analyst_note", "")) or "No analyst note provided."
        evidence = data.get("evidence")
        return score, note, evidence
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    score = None
    note = ""
    evidence = None

    score_match = re.search(r"anomaly(?:\s+score)?\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)", cleaned, re.IGNORECASE)
    if score_match:
        score = _safe_float(score_match.group(1))

    note_match = re.search(
        r"analyst(?:\s+note)?\s*[:=-]\s*(.+)", cleaned, re.IGNORECASE
    )
    if note_match:
        note = note_match.group(1).strip()

    if not note:
        # Fall back to the first non-empty line
        for line in cleaned.splitlines():
            if line.strip():
                note = line.strip()
                break

    return score, note or "No analyst note provided.", evidence


def _safe_float(value: object) -> Optional[float]:
    """Best-effort conversion of model provided scores to a [0, 1] float.

    The language model does not always return a clean float.  It may add
    annotations such as "0.75 (High)", percentages like "75%", or even spell the
    value out as part of a longer sentence.  This helper extracts the first
    numeric token from the string, interprets percentages, and normalises the
    result into the expected probability range.
    """

    if value is None:
        return None

    is_percentage = False

    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None

        match = re.search(r"-?[0-9]+(?:\.[0-9]+)?", cleaned)
        if not match:
            return None

        number = float(match.group())

        if "%" in cleaned or "percent" in cleaned.lower():
            number /= 100.0
            is_percentage = True
    else:
        return None

    if number < 0:
        number = 0.0

    if number > 1.0:
        if not is_percentage and number <= 100.0:
            number /= 100.0
        elif not is_percentage:
            return None

    return min(number, 1.0)
