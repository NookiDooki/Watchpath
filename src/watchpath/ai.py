"""AI integration utilities for Watchpath."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence


@dataclass
class SessionAnalysis:
    """Structured response produced by the language model."""

    session_id: str
    anomaly_score: Optional[float]
    analyst_note: str
    evidence: str | list[str] | None
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
        "Provide an anomaly score between 0 and 1, capture structured analyst "
        "context, and highlight supporting evidence. Respond with JSON "
        "containing `anomaly_score`, an `analyst_note` object with summary, "
        "impact, action, confidence, and an `evidence` array of objects with "
        "`log_excerpt` and `reason`.\n"
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


def _parse_analysis_output(output: str) -> tuple[Optional[float], str, str | list[str] | None]:
    """Extract structured information from a model response."""

    cleaned = output.strip()
    if not cleaned:
        return None, "No analyst note returned.", None

    # Try JSON first
    try:
        data = json.loads(cleaned)
        score = _safe_float(data.get("anomaly_score"))
        note = _normalise_analyst_note(data.get("analyst_note"))
        evidence = _normalise_evidence_payload(data.get("evidence"))
        return score, note, evidence
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    score = None
    note = _normalise_analyst_note(None)
    evidence: str | list[str] | None = None

    score_match = re.search(r"anomaly(?:\s+score)?\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)", cleaned, re.IGNORECASE)
    if score_match:
        score = _safe_float(score_match.group(1))

    if score is None:
        percent_match = re.search(r"\(([0-9]{1,3})%\)", cleaned)
        if percent_match:
            score = _safe_float(percent_match.group(1) + "%")

    if score is None:
        anomaly_lines = [line for line in cleaned.splitlines() if "anomaly" in line.lower()]
        for line in anomaly_lines:
            percent_match = re.search(r"([0-9]{1,3})%", line)
            if percent_match:
                score = _safe_float(percent_match.group(1) + "%")
                break

    note_match = re.search(
        r"analyst(?:\s+note)?\s*[:=-]\s*(.+)", cleaned, re.IGNORECASE
    )
    if note_match:
        note = _normalise_analyst_note(note_match.group(1).strip())

    if not note or note == "No analyst note provided.":
        # Fall back to the first non-empty line
        for line in cleaned.splitlines():
            if line.strip():
                note = _normalise_analyst_note(line.strip())
                if note:
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


def _normalise_analyst_note(note: Any) -> str:
    """Convert various note representations into a consistent multiline string."""

    def _clean_segment(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return text

    if isinstance(note, dict):
        summary = _clean_segment(note.get("summary"))
        impact = _clean_segment(note.get("impact"))
        action = _clean_segment(note.get("action"))
        confidence = _clean_segment(note.get("confidence"))

        parts = []
        for label, content in ("Summary", summary), ("Impact", impact), ("Action", action):
            if content:
                fragment = content.rstrip()
                if fragment and fragment[-1] not in ".!?":
                    fragment += "."
                parts.append(f"{label}: {fragment}")

        if confidence:
            parts.append(f"Confidence: {confidence}")

        return "\n".join(parts) or "No analyst note provided."

    if isinstance(note, Sequence) and not isinstance(note, (str, bytes, bytearray)):
        flattened = [segment for segment in (_normalise_analyst_note(item) for item in note) if segment]
        if flattened:
            return "\n".join(dict.fromkeys(flattened))
        return "No analyst note provided."

    if note is None:
        return "No analyst note provided."

    text = _clean_segment(note)
    if not text:
        return "No analyst note provided."

    return text


def _normalise_evidence_payload(evidence: Any) -> list[str] | None:
    """Standardise evidence payloads coming from the model."""

    if evidence is None:
        return None

    if isinstance(evidence, (str, bytes, bytearray)):
        text = evidence.decode("utf-8") if isinstance(evidence, (bytes, bytearray)) else evidence
        cleaned = text.strip()
        return [cleaned] if cleaned else None

    if isinstance(evidence, dict):
        log_excerpt = str(evidence.get("log_excerpt", "")).strip()
        reason = str(evidence.get("reason", "")).strip()
        if log_excerpt and reason:
            return [f"{log_excerpt} — {reason}"]
        if log_excerpt:
            return [log_excerpt]
        if reason:
            return [reason]
        return None

    if isinstance(evidence, Sequence):
        collected: list[str] = []
        for item in evidence:
            normalised = _normalise_evidence_payload(item)
            if normalised:
                collected.extend(normalised)
        return collected or None

    text = str(evidence).strip()
    return [text] if text else None
