"""Utilities for parsing Apache access logs and generating analytical charts."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOG_PATTERN = re.compile(
    r"(?P<ip>\S+)\s+"  # IP address
    r"(?P<ident>\S+)\s+"  # RFC 1413 identity of the client
    r"(?P<user>\S+)\s+"  # userid of the person requesting the document
    r"\[(?P<time>[^\]]+)\]\s+"
    r"\"(?P<request>[^\"]*)\"\s+"
    r"(?P<status>\d{3})\s+"
    r"(?P<size>\S+)\s+"
    r"\"(?P<referer>[^\"]*)\"\s+"
    r"\"(?P<user_agent>[^\"]*)\""
)


@dataclass
class LogEntry:
    ip: str
    ident: str
    user: str
    timestamp: Optional[datetime]
    method: Optional[str]
    path: Optional[str]
    protocol: Optional[str]
    status: Optional[int]
    size: Optional[int]
    referer: str
    user_agent: str


@dataclass
class Aggregates:
    entries: List[LogEntry]
    status_counts: Counter
    ip_counts: Counter
    endpoint_counts: Counter
    user_agent_counts: Counter
    requests_per_minute: Counter
    total_bytes: int

    @property
    def total_requests(self) -> int:
        return len(self.entries)

    @property
    def unique_ips(self) -> int:
        return len(self.ip_counts)


@dataclass
class ChartMetadata:
    filename: str
    description: str
    metrics: Dict[str, str]


TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


def parse_apache_logs(log_path: Path) -> List[LogEntry]:
    """Parse the provided Apache access log file into structured entries."""
    entries: List[LogEntry] = []
    for line in log_path.read_text().splitlines():
        match = LOG_PATTERN.match(line)
        if not match:
            continue

        data = match.groupdict()
        raw_time = data.get("time")
        timestamp: Optional[datetime] = None
        if raw_time:
            try:
                timestamp = datetime.strptime(raw_time, TIME_FORMAT)
            except ValueError:
                timestamp = None

        request = data.get("request") or ""
        method: Optional[str] = None
        path: Optional[str] = None
        protocol: Optional[str] = None
        if request and request != "-":
            parts = request.split()
            if len(parts) == 3:
                method, path, protocol = parts
            elif len(parts) == 2:
                method, path = parts
            elif len(parts) == 1:
                path = parts[0]

        size_str = data.get("size", "0")
        try:
            size = int(size_str) if size_str != "-" else 0
        except ValueError:
            size = 0

        try:
            status = int(data.get("status", ""))
        except ValueError:
            status = None

        entries.append(
            LogEntry(
                ip=data.get("ip", "-"),
                ident=data.get("ident", "-"),
                user=data.get("user", "-"),
                timestamp=timestamp,
                method=method,
                path=path,
                protocol=protocol,
                status=status,
                size=size,
                referer=data.get("referer", ""),
                user_agent=data.get("user_agent", ""),
            )
        )
    return entries


def aggregate_metrics(entries: Iterable[LogEntry]) -> Aggregates:
    entries_list = list(entries)
    status_counts: Counter = Counter()
    ip_counts: Counter = Counter()
    endpoint_counts: Counter = Counter()
    user_agent_counts: Counter = Counter()
    requests_per_minute: Counter = Counter()
    total_bytes = 0

    for entry in entries_list:
        if entry.status is not None:
            status_counts[str(entry.status)] += 1
        if entry.ip:
            ip_counts[entry.ip] += 1
        if entry.path:
            endpoint_counts[entry.path] += 1
        if entry.user_agent:
            user_agent_counts[entry.user_agent] += 1
        if entry.timestamp:
            ts = entry.timestamp
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc)
            ts = ts.replace(second=0, microsecond=0, tzinfo=None)
            requests_per_minute[ts] += 1
        if entry.size is not None:
            total_bytes += entry.size

    return Aggregates(
        entries=entries_list,
        status_counts=status_counts,
        ip_counts=ip_counts,
        endpoint_counts=endpoint_counts,
        user_agent_counts=user_agent_counts,
        requests_per_minute=requests_per_minute,
        total_bytes=total_bytes,
    )


def _format_top_items(counter: Counter, limit: int = 5) -> str:
    if not counter:
        return "n/a"
    items = counter.most_common(limit)
    return ", ".join(f"{key}={value}" for key, value in items)


def build_summary_context(aggregates: Aggregates) -> str:
    lines = [
        f"Total requests: {aggregates.total_requests}",
        f"Unique IPs: {aggregates.unique_ips}",
        f"Total bytes transferred: {aggregates.total_bytes}",
        f"Top status codes: {_format_top_items(aggregates.status_counts)}",
        f"Top endpoints: {_format_top_items(aggregates.endpoint_counts)}",
        f"Top user agents: {_format_top_items(aggregates.user_agent_counts)}",
        f"Top IPs: {_format_top_items(aggregates.ip_counts)}",
    ]
    if aggregates.requests_per_minute:
        time_range = (
            min(aggregates.requests_per_minute.keys()),
            max(aggregates.requests_per_minute.keys()),
        )
        lines.append(
            "Request timeline: {} – {}".format(
                time_range[0].isoformat(timespec="minutes"),
                time_range[1].isoformat(timespec="minutes"),
            )
        )
    else:
        lines.append("Request timeline: n/a")
    return "\n".join(lines)


def generate_charts(aggregates: Aggregates, output_dir: Path) -> List[ChartMetadata]:
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_metadata: List[ChartMetadata] = []

    if aggregates.status_counts:
        filename = "requests_by_status.png"
        labels, values = zip(*aggregates.status_counts.most_common())
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(labels, values, color="#2a5298")
        ax.set_xlabel("HTTP Status Code")
        ax.set_ylabel("Requests")
        ax.set_title("Requests by Status Code")
        for idx, val in enumerate(values):
            ax.text(idx, val + max(values) * 0.01, str(val), ha="center", va="bottom")
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
        chart_metadata.append(
            ChartMetadata(
                filename=filename,
                description="Bar chart showing request counts by HTTP status code.",
                metrics={code: str(count) for code, count in aggregates.status_counts.most_common()},
            )
        )

    if aggregates.requests_per_minute:
        filename = "requests_over_time.png"
        sorted_points = sorted(aggregates.requests_per_minute.items())
        times = [point[0] for point in sorted_points]
        counts = [point[1] for point in sorted_points]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(times, counts, marker="o", color="#1e3c72")
        ax.set_xlabel("Timestamp (UTC, minute)")
        ax.set_ylabel("Requests")
        ax.set_title("Requests per Minute")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
        chart_metadata.append(
            ChartMetadata(
                filename=filename,
                description="Line chart of request volume per minute (UTC).",
                metrics={dt.isoformat(): str(count) for dt, count in sorted_points[:10]},
            )
        )

    if aggregates.ip_counts:
        filename = "top_ips.png"
        top_ips = aggregates.ip_counts.most_common(5)
        labels = [item[0] for item in top_ips]
        values = [item[1] for item in top_ips]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh(range(len(labels)), values, color="#5170a3")
        ax.set_xlabel("Requests")
        ax.set_ylabel("IP Address")
        ax.set_title("Top IP Addresses by Request Volume")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        for idx, val in enumerate(values):
            ax.text(val + max(values) * 0.01, idx, str(val), va="center")
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
        chart_metadata.append(
            ChartMetadata(
                filename=filename,
                description="Horizontal bar chart of the top IP addresses by request count.",
                metrics={ip: str(count) for ip, count in top_ips},
            )
        )

    if aggregates.endpoint_counts:
        filename = "top_endpoints.png"
        top_endpoints = aggregates.endpoint_counts.most_common(5)
        labels = [item[0] for item in top_endpoints]
        values = [item[1] for item in top_endpoints]
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.barh(range(len(labels)), values, color="#26466d")
        ax.set_xlabel("Requests")
        ax.set_ylabel("Endpoint")
        ax.set_title("Top Endpoints by Request Volume")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        for idx, val in enumerate(values):
            ax.text(val + max(values) * 0.01, idx, str(val), va="center")
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
        chart_metadata.append(
            ChartMetadata(
                filename=filename,
                description="Horizontal bar chart of the busiest endpoints in the log sample.",
                metrics={endpoint: str(count) for endpoint, count in top_endpoints},
            )
        )

    return chart_metadata


def build_chart_context(chart_metadata: Iterable[ChartMetadata]) -> str:
    items = list(chart_metadata)
    if not items:
        return "No charts were generated for this log chunk."
    lines = []
    for chart in items:
        metrics_summary = ", ".join(f"{k}={v}" for k, v in chart.metrics.items()) or "n/a"
        lines.append(f"{chart.filename}: {chart.description} Key figures -> {metrics_summary}.")
    return "\n".join(lines)
