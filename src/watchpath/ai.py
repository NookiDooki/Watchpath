"""AI integration utilities for Watchpath."""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
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
    enriched_note, enriched_evidence = _enrich_analysis(
        analyst_note, evidence, log_chunk
    )

    return SessionAnalysis(
        session_id=session_id,
        anomaly_score=anomaly_score,
        analyst_note=enriched_note,
        evidence=enriched_evidence,
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


def _enrich_analysis(
    analyst_note: str,
    evidence: str | Sequence[str] | None,
    log_chunk: str,
) -> tuple[str, str | list[str] | None]:
    """Augment sparse model output with heuristics from the raw logs."""

    insights, derived_evidence = _analyse_log_chunk(log_chunk)

    informative_note = _note_is_informative(analyst_note)
    if informative_note:
        enriched_note = analyst_note
    else:
        fallback = "\n".join(insights) if insights else "No analyst note provided."
        enriched_note = fallback

    evidence_is_useful = _evidence_is_informative(evidence, log_chunk)
    if evidence_is_useful:
        enriched_evidence: str | list[str] | None
        if isinstance(evidence, (bytes, bytearray)):
            enriched_evidence = evidence.decode("utf-8", errors="ignore")
        elif isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes, bytearray)):
            enriched_evidence = [str(item).strip() for item in evidence if str(item).strip()]
        else:
            enriched_evidence = evidence  # type: ignore[assignment]
    elif derived_evidence:
        enriched_evidence = derived_evidence
    else:
        enriched_evidence = None

    return enriched_note, enriched_evidence


def _note_is_informative(note: str | None) -> bool:
    if not note:
        return False

    cleaned = str(note).strip()
    if not cleaned:
        return False

    lowered = cleaned.lower()
    if lowered in {"no analyst note provided.", "n/a", "none"}:
        return False

    if re.fullmatch(r"(anomaly\s*)?score[:\s]*[0-9.]+%?", lowered):
        return False

    if re.fullmatch(r"[0-9.]+%?", lowered):
        return False

    alnum = re.sub(r"[^a-z0-9]", "", lowered)
    return len(alnum) > 6


def _evidence_is_informative(
    evidence: str | Sequence[str] | bytes | bytearray | None,
    log_chunk: str,
) -> bool:
    if evidence is None:
        return False

    log_text = _normalise_logs(log_chunk)

    if isinstance(evidence, (bytes, bytearray)):
        evidence_text = evidence.decode("utf-8", errors="ignore").strip()
        return bool(evidence_text) and evidence_text != log_text

    if isinstance(evidence, str):
        trimmed = evidence.strip()
        return bool(trimmed) and trimmed != log_text

    if isinstance(evidence, Sequence):
        cleaned = [str(item).strip() for item in evidence if str(item).strip()]
        if not cleaned:
            return False
        if len(cleaned) == 1 and cleaned[0] == log_text:
            return False
        return True

    return True


def _analyse_log_chunk(log_chunk: str) -> tuple[list[str], list[str]]:
    entries = _parse_log_entries(log_chunk)
    if not entries:
        return [], []

    note_segments: list[str] = []
    evidence_lines: list[str] = []
    evidence_set: set[str] = set()

    total_requests = len(entries)
    path_counter = Counter(entry.path for entry in entries if entry.path)
    method_counter = Counter(entry.method for entry in entries if entry.method)
    status_counter = Counter(entry.status for entry in entries)
    error_counter: Counter[tuple[int, str, str]] = Counter()
    pair_counter: Counter[tuple[str, str]] = Counter()
    status_by_pair: defaultdict[tuple[str, str], Counter[int]] = defaultdict(Counter)
    login_failures = 0

    for entry in entries:
        pair = (entry.method, entry.path)
        pair_counter[pair] += 1
        status_by_pair[pair][entry.status] += 1
        if entry.status >= 400:
            error_counter[(entry.status, entry.method, entry.path)] += 1
            if "login" in entry.path.lower():
                login_failures += 1

    if error_counter:
        total_errors = sum(error_counter.values())
        fragments: list[str] = []
        for (status, method, path), count in error_counter.most_common(3):
            fragment = f"{count}× {method} {path} → {status}"
            fragments.append(fragment)
            if fragment not in evidence_set:
                evidence_lines.append(fragment)
                evidence_set.add(fragment)
        detail = "; ".join(fragments)
        note_segments.append(
            f"Detected {total_errors} error response{'s' if total_errors != 1 else ''} ({detail})."
        )

    if login_failures:
        note_segments.append(
            f"Observed {login_failures} failed login attempt{'s' if login_failures != 1 else ''}."
        )

    repeated_paths = [item for item in path_counter.items() if item[1] >= 3]
    if repeated_paths:
        repeated_paths.sort(key=lambda item: (-item[1], item[0]))
        summaries: list[str] = []
        for path, count in repeated_paths[:3]:
            methods = sorted({entry.method for entry in entries if entry.path == path})
            method_text = ", ".join(methods) if methods else "unknown methods"
            fragment = f"{count}× {path} via {method_text}"
            summaries.append(fragment)
            if fragment not in evidence_set:
                evidence_lines.append(fragment)
                evidence_set.add(fragment)
        note_segments.append(
            "Repeated access patterns: " + "; ".join(summaries) + "."
        )

    write_methods = {"POST", "PUT", "DELETE", "PATCH"}
    write_targets = [item for item in pair_counter.items() if item[0][0] in write_methods]
    if write_targets:
        write_targets.sort(key=lambda item: (-item[1], item[0][1]))
        fragments = []
        for (method, path), count in write_targets[:3]:
            status_summary = ", ".join(
                f"{status}×{freq}" for status, freq in status_by_pair[(method, path)].most_common()
            )
            fragment = f"{count}× {method} {path} ({status_summary})"
            fragments.append(fragment)
            if fragment not in evidence_set:
                evidence_lines.append(fragment)
                evidence_set.add(fragment)
        note_segments.append("Write operations observed: " + "; ".join(fragments) + ".")

    if not note_segments:
        unique_paths = len(path_counter)
        dominant_method = method_counter.most_common(1)[0][0] if method_counter else "GET"
        dominant_status = status_counter.most_common(1)[0][0] if status_counter else 200
        note_segments.append(
            "Routine activity detected: "
            f"{total_requests} request{'s' if total_requests != 1 else ''} "
            f"across {unique_paths} path{'s' if unique_paths != 1 else ''}, "
            f"primarily {dominant_method} with status {dominant_status}."
        )

    return note_segments, evidence_lines


_LOG_ENTRY_PATTERN = re.compile(
    r'"(?P<method>[A-Z]+)\s+(?P<path>[^"\s]+)[^\"]*"\s+(?P<status>\d{3})\s+(?P<size>\S+)'
)


@dataclass
class _ParsedLogEntry:
    method: str
    path: str
    status: int


def _parse_log_entries(log_chunk: str) -> list[_ParsedLogEntry]:
    entries: list[_ParsedLogEntry] = []
    for line in log_chunk.splitlines():
        if not line.strip():
            continue
        match = _LOG_ENTRY_PATTERN.search(line)
        if not match:
            continue
        method = match.group("method")
        path = match.group("path")
        status = int(match.group("status"))
        entries.append(_ParsedLogEntry(method=method, path=path, status=status))
    return entries


def _normalise_logs(log_chunk: str) -> str:
    return "\n".join(line.strip() for line in log_chunk.splitlines() if line.strip())


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
