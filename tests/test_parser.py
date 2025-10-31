from datetime import timedelta

import pytest

from watchpath.ai import SessionAnalysis
from watchpath.parser import (
    build_session_payload,
    chunk_log_file,
    format_session_markdown,
    format_session_report,
    load_sessions,
    summarize_sessions,
)


LOG_TEMPLATE = (
    "{ip} - {user} [{timestamp}] \"{method} {path} HTTP/1.1\" {status} {size} \"-\" \"Mozilla/5.0\""
)


def _write_log(tmp_path, lines):
    log_file = tmp_path / "access.log"
    log_file.write_text("\n".join(lines) + "\n")
    return log_file


def test_load_sessions_groups_by_inactivity(tmp_path):
    lines = [
        LOG_TEMPLATE.format(
            ip="192.168.1.10",
            user="-",
            timestamp="02/Mar/2025:09:00:01 +0000",
            method="GET",
            path="/index.html",
            status=200,
            size=512,
        ),
        LOG_TEMPLATE.format(
            ip="192.168.1.10",
            user="-",
            timestamp="02/Mar/2025:09:05:01 +0000",
            method="POST",
            path="/login",
            status=302,
            size=128,
        ),
        LOG_TEMPLATE.format(
            ip="192.168.1.10",
            user="-",
            timestamp="02/Mar/2025:09:25:02 +0000",
            method="GET",
            path="/dashboard",
            status=200,
            size=1024,
        ),
    ]

    log_file = _write_log(tmp_path, lines)
    sessions = load_sessions(str(log_file), inactivity_window=timedelta(minutes=10))

    assert len(sessions) == 2
    assert sessions[0].records[0].path == "/index.html"
    assert sessions[1].records[0].path == "/dashboard"


def test_summarize_sessions_and_format_report(tmp_path):
    lines = [
        LOG_TEMPLATE.format(
            ip="192.168.1.11",
            user="alice",
            timestamp="02/Mar/2025:10:00:00 +0000",
            method="GET",
            path="/home",
            status=200,
            size=600,
        ),
        LOG_TEMPLATE.format(
            ip="192.168.1.11",
            user="alice",
            timestamp="02/Mar/2025:10:02:00 +0000",
            method="GET",
            path="/reports",
            status=200,
            size=700,
        ),
        LOG_TEMPLATE.format(
            ip="192.168.1.12",
            user="-",
            timestamp="02/Mar/2025:10:05:00 +0000",
            method="POST",
            path="/api/data",
            status=201,
            size=256,
        ),
    ]
    log_file = _write_log(tmp_path, lines)

    sessions = load_sessions(str(log_file))
    stats = summarize_sessions(sessions)

    assert pytest.approx(stats.mean_session_duration, rel=0.01) == 120.0
    assert stats.ip_distribution["192.168.1.11"] == 1
    assert stats.request_counts["GET"] == 2
    assert stats.status_distribution[200] == 2
    assert stats.request_timeline

    first_session = sessions[0]
    analysis = SessionAnalysis(
        session_id=first_session.session_id,
        anomaly_score=0.25,
        analyst_note="Normal browsing behaviour",
        evidence="\n".join(record.raw for record in first_session.records),
        raw_response="{}",
    )

    report = format_session_report(first_session, analysis, stats)
    assert "⚠️" in report
    assert "🧠" in report
    assert "📊" in report
    assert "192.168.1.11" in report

    markdown = format_session_markdown(first_session, analysis, stats)
    assert markdown.startswith("### Session")
    assert "**IP**" in markdown

    payload = build_session_payload(first_session, analysis, stats)
    assert payload["session_id"] == first_session.session_id
    assert payload["session_stats"]["request_count"] == len(first_session.records)
    assert "global_stats" in payload
    assert payload["records"]


def test_chunk_log_file_reads_chunks(tmp_path):
    lines = [
        LOG_TEMPLATE.format(
            ip="192.168.1.13",
            user="-",
            timestamp="02/Mar/2025:11:00:00 +0000",
            method="GET",
            path=f"/item/{idx}",
            status=200,
            size=123,
        )
        for idx in range(5)
    ]
    log_file = _write_log(tmp_path, lines)

    chunks = list(chunk_log_file(str(log_file), chunk_size=2))

    assert len(chunks) == 3
    assert chunks[0].count("\n") == 1
