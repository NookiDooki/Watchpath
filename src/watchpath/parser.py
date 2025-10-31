"""Utilities for parsing and summarising web server logs."""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .ai import SessionAnalysis

# ╭──────────────────────────────────────────────────────────────╮
# │ Pattern and timing defaults reused throughout the module.   │
# ╰──────────────────────────────────────────────────────────────╯
LOG_PATTERN = re.compile(
    r"(?P<ip>\S+)\s+(?P<ident>\S+)\s+(?P<user>\S+)\s+\[(?P<time>[^\]]+)\]\s+\"(?P<request>[^\"]*)\"\s+"
    r"(?P<status>\d{3})\s+(?P<size>\S+)\s+\"(?P<referrer>[^\"]*)\"\s+\"(?P<agent>[^\"]*)\""
)

TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
DEFAULT_INACTIVITY_WINDOW = timedelta(minutes=15)


# ╭──────────────────────────────────────────────────────────────╮
# │ Core data structures                                         │
# ╰──────────────────────────────────────────────────────────────╯


@dataclass
class LogRecord:
    """A parsed Apache/Nginx access log entry."""

    ip: str
    ident: str
    user: str
    timestamp: datetime
    method: str
    path: str
    protocol: str
    status: int
    size: int
    referrer: str
    user_agent: str
    raw: str


@dataclass
class Session:
    """Logical collection of log records for a single visitor."""

    session_id: str
    ip: str
    user: str
    records: List[LogRecord]

    @property
    def start(self) -> Optional[datetime]:
        return self.records[0].timestamp if self.records else None

    @property
    def end(self) -> Optional[datetime]:
        return self.records[-1].timestamp if self.records else None

    @property
    def duration(self) -> Optional[timedelta]:
        if not self.records:
            return None
        return self.records[-1].timestamp - self.records[0].timestamp


@dataclass
class SessionStatistics:
    """Aggregate metrics computed across all sessions."""

    mean_session_duration: float
    ip_distribution: Dict[str, int]
    request_counts: Dict[str, int]
    status_distribution: Dict[int, int]
    request_timeline: List[Tuple[str, int]]


    

# ╭──────────────────────────────────────────────────────────────╮
# │ Parsing helpers                                              │
# ╰──────────────────────────────────────────────────────────────╯


def chunk_log_file(log_path: str, chunk_size: int = 50) -> Iterable[str]:
    """Yield raw log lines from ``log_path`` in chunks of ``chunk_size``."""

    lines = Path(log_path).read_text().splitlines()
    for index in range(0, len(lines), chunk_size):
        yield "\n".join(lines[index : index + chunk_size])


def parse_log_line(line: str) -> Optional[LogRecord]:
    """Parse a single access log line into a :class:`LogRecord`."""

    # Each line is matched with the compiled regex. A ``None`` result means
    # the entry is malformed and should be ignored gracefully.

    match = LOG_PATTERN.match(line)
    if not match:
        return None

    time_str = match.group("time")
    try:
        timestamp = datetime.strptime(time_str, TIME_FORMAT)
    except ValueError:
        return None

    request = match.group("request").split()
    # Requests sometimes omit pieces (for example when the method is missing),
    # so we pad the result to avoid ``IndexError`` surprises downstream.
    method, path, protocol = (request + ["", "", ""])[:3]

    size_token = match.group("size")
    size = int(size_token) if size_token.isdigit() else 0

    return LogRecord(
        ip=match.group("ip"),
        ident=match.group("ident"),
        user=match.group("user") if match.group("user") != "-" else "",
        timestamp=timestamp,
        method=method,
        path=path,
        protocol=protocol,
        status=int(match.group("status")),
        size=size,
        referrer=match.group("referrer"),
        user_agent=match.group("agent"),
        raw=line,
    )


def load_sessions(
    log_path: str,
    *,
    inactivity_window: timedelta = DEFAULT_INACTIVITY_WINDOW,
) -> List[Session]:
    """Parse ``log_path`` and group records into sessions."""

    lines = Path(log_path).read_text().splitlines()
    records = [parse_log_line(line) for line in lines if line.strip()]
    records = [record for record in records if record is not None]
    records.sort(key=lambda record: record.timestamp)

    sessions: List[Session] = []
    active_sessions: Dict[tuple[str, str], Session] = {}
    counters: Dict[tuple[str, str], int] = defaultdict(int)

    for record in records:
        key = (record.ip, record.user)
        existing = active_sessions.get(key)
        start_new = True
        if existing and existing.records:
            delta = record.timestamp - existing.records[-1].timestamp
            if delta <= inactivity_window:
                start_new = False

        if start_new:
            counters[key] += 1
            label_user = record.user or "anon"
            session_id = f"{record.ip}-{label_user}-{counters[key]}"
            existing = Session(session_id=session_id, ip=record.ip, user=record.user or "-", records=[])
            sessions.append(existing)
            active_sessions[key] = existing

        existing.records.append(record)
        active_sessions[key] = existing

    return sessions


def summarize_sessions(sessions: Iterable[Session]) -> SessionStatistics:
    """Compute aggregate metrics for the supplied sessions."""

    # Convert to a list so we can iterate multiple times without exhausting an
    # iterator passed by the caller. This keeps the function ergonomic in the
    # CLI and GUI pipelines where generators are common.

    session_list = list(sessions)
    durations = [session.duration.total_seconds() for session in session_list if session.duration]
    mean_duration = statistics.mean(durations) if durations else 0.0

    ip_counts = Counter(session.ip for session in session_list)

    request_counts: Counter[str] = Counter()
    status_counts: Counter[int] = Counter()
    timeline_counts: Counter[datetime] = Counter()
    for session in session_list:
        for record in session.records:
            request_counts.update([record.method or "UNKNOWN"])
            status_counts.update([record.status])
            # Normalise to minute precision for the global sparkline chart so
            # the GUI can render smooth sparklines without jitter.
            minute = record.timestamp.replace(second=0, microsecond=0)
            timeline_counts[minute] += 1

    timeline_points = [
        (moment.isoformat(), count)
        for moment, count in sorted(timeline_counts.items())
    ]

    return SessionStatistics(
        mean_session_duration=mean_duration,
        ip_distribution=dict(ip_counts),
        request_counts=dict(request_counts),
        status_distribution=dict(status_counts),
        request_timeline=timeline_points,
    )


def build_session_payload(
    session: Session,
    analysis: SessionAnalysis,
    global_stats: SessionStatistics,
) -> Dict[str, object]:
    """Return a JSON-serialisable representation of a session report."""

    duration_seconds = session.duration.total_seconds() if session.duration else 0.0
    unique_paths = sorted({record.path for record in session.records if record.path})
    # Collect method counts so both the CLI and GUI can render summaries.
    method_counts = Counter(record.method or "UNKNOWN" for record in session.records)

    top_ips = sorted(
        global_stats.ip_distribution.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]

    return {
        "session_id": session.session_id,
        "ip": session.ip,
        "user": session.user or "-",
        "anomaly_score": analysis.anomaly_score,
        "analyst_note": analysis.analyst_note,
        "evidence": analysis.evidence,
        "raw_logs": [record.raw for record in session.records],
        "session_stats": {
            "duration_seconds": duration_seconds,
            "request_count": len(session.records),
            "unique_path_count": len(unique_paths),
            "unique_paths": unique_paths,
            "method_counts": dict(method_counts),
        },
        "global_stats": {
            "mean_session_duration_seconds": global_stats.mean_session_duration,
            "ip_distribution": dict(global_stats.ip_distribution),
            "request_counts": dict(global_stats.request_counts),
            "top_ips": top_ips,
            "status_distribution": dict(global_stats.status_distribution),
            "request_timeline": list(global_stats.request_timeline),
        },
        "records": [
            {
                "timestamp": record.timestamp.isoformat(),
                "method": record.method,
                "path": record.path,
                "status": record.status,
                "size": record.size,
                "referrer": record.referrer,
                "user_agent": record.user_agent,
            }
            for record in session.records
        ],
    }


def _format_duration(seconds: float) -> str:
    return str(timedelta(seconds=int(round(seconds))))


def _normalise_evidence(evidence: object) -> list[str]:
    """Return a flat list of evidence strings from ``evidence``."""

    # The language model may emit strings, arrays, or nested objects. This
    # helper smooths those possibilities into a simple list used by renderers.

    if evidence is None:
        return []

    if isinstance(evidence, str):
        text = evidence.strip()
        return [text] if text else []

    if isinstance(evidence, Sequence) and not isinstance(evidence, (bytes, bytearray, str)):
        collected: list[str] = []
        for item in evidence:
            collected.extend(_normalise_evidence(item))
        return collected

    return [str(evidence)]


def _render_text_from_payload(payload: Dict[str, object]) -> str:
    session_stats = payload["session_stats"]
    global_stats = payload["global_stats"]

    method_counts = session_stats["method_counts"]
    method_summary = ", ".join(
        f"{method} ({count})" for method, count in Counter(method_counts).most_common()
    ) or "None"

    ip_summary = ", ".join(
        f"{ip}: {count}" for ip, count in global_stats["top_ips"]
    ) or "None"

    request_summary = ", ".join(
        f"{method}: {count}"
        for method, count in sorted(global_stats["request_counts"].items())
    ) or "None"

    lines = [
        f"Session {payload['session_id']} (IP: {payload['ip']}, User: {payload['user']})",
        f"⚠️ Anomaly Score: {payload['anomaly_score'] if payload['anomaly_score'] is not None else 'N/A'}",
        f"🧠 Analyst Note: {payload['analyst_note']}",
        "📊 Session Statistics:",
        f"  • Duration: {_format_duration(session_stats['duration_seconds'])}",
        f"  • Requests: {session_stats['request_count']}",
        f"  • Unique Paths: {session_stats['unique_path_count']}",
        f"  • Methods: {method_summary}",
        "📊 Global Statistics:",
        f"  • Mean Session Duration: {_format_duration(global_stats['mean_session_duration_seconds'])}",
        f"  • Top IPs: {ip_summary}",
        f"  • Request Distribution: {request_summary}",
    ]

    evidence_items = _normalise_evidence(payload.get("evidence"))
    raw_joined = "\n".join(payload["raw_logs"])
    if evidence_items and not (len(evidence_items) == 1 and evidence_items[0] == raw_joined):
        if len(evidence_items) == 1:
            lines.append("  • Evidence: " + evidence_items[0])
        else:
            lines.append("  • Evidence:")
            lines.extend("    - " + item for item in evidence_items)

    return "\n".join(lines)


def _render_markdown_from_payload(payload: Dict[str, object]) -> str:
    session_stats = payload["session_stats"]
    global_stats = payload["global_stats"]

    method_counts = Counter(session_stats["method_counts"])
    method_lines = [
        f"        - **{method}**: {count}" for method, count in method_counts.most_common()
    ] or ["        - None"]

    ip_lines = [
        f"        - **{ip}**: {count}" for ip, count in global_stats["top_ips"]
    ] or ["        - None"]

    request_lines = [
        f"        - **{method}**: {count}"
        for method, count in sorted(global_stats["request_counts"].items())
    ] or ["        - None"]

    unique_path_lines = [
        f"        - `{path}`" for path in session_stats["unique_paths"]
    ] or ["        - None"]

    markdown = [
        f"### Session `{payload['session_id']}`",
        "",
        f"- **IP**: `{payload['ip']}`",
        f"- **User**: `{payload['user']}`",
        f"- **⚠️ Anomaly Score**: {payload['anomaly_score'] if payload['anomaly_score'] is not None else 'N/A'}",
        f"- **🧠 Analyst Note**: {payload['analyst_note']}",
        "- **📊 Session Statistics**:",
        f"    - Duration: {_format_duration(session_stats['duration_seconds'])}",
        f"    - Requests: {session_stats['request_count']}",
        f"    - Unique Paths ({session_stats['unique_path_count']}):",
        *unique_path_lines,
        "    - Methods:",
        *method_lines,
        "- **📊 Global Statistics**:",
        f"    - Mean Session Duration: {_format_duration(global_stats['mean_session_duration_seconds'])}",
        "    - Top IPs:",
        *ip_lines,
        "    - Request Distribution:",
        *request_lines,
    ]

    evidence_items = _normalise_evidence(payload.get("evidence"))
    if evidence_items:
        markdown.append("- **Evidence**:")
        for item in evidence_items:
            formatted = item.replace("\n", "\n    > ")
            markdown.append(f"    > {formatted}")

    return "\n".join(markdown)


def format_session_report(
    session: Session,
    analysis: SessionAnalysis,
    global_stats: SessionStatistics,
) -> str:
    """Combine structured data and AI notes into a rich session report."""

    payload = build_session_payload(session, analysis, global_stats)
    return _render_text_from_payload(payload)


def format_session_markdown(
    session: Session,
    analysis: SessionAnalysis,
    global_stats: SessionStatistics,
) -> str:
    """Return a Markdown representation of a session report."""

    payload = build_session_payload(session, analysis, global_stats)
    return _render_markdown_from_payload(payload)


def build_session_chunk(session: Session, chunk_size: int) -> str:
    """Return at most ``chunk_size`` raw log lines from ``session``."""

    size = max(1, chunk_size)
    return "\n".join(record.raw for record in session.records[:size])
