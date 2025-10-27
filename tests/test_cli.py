import json
from pathlib import Path

import pytest

from watchpath import cli
from watchpath.ai import SessionAnalysis

LOG_LINE = "192.168.1.20 - bob [02/Mar/2025:12:00:00 +0000] \"GET /secure HTTP/1.1\" 200 420 \"-\" \"Mozilla/5.0\""


@pytest.fixture()
def tmp_log(tmp_path):
    log_file = tmp_path / "access.log"
    log_file.write_text(LOG_LINE + "\n")
    return log_file


@pytest.fixture()
def prompt_file(tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("You are a SOC analyst.")
    return prompt


def test_cli_parse_outputs_report(monkeypatch, capsys, tmp_log, prompt_file):
    def fake_analyze(session_id, log_chunk, prompt_path, model):
        return SessionAnalysis(
            session_id=session_id,
            anomaly_score=0.9,
            analyst_note="Suspicious access to /secure endpoint.",
            evidence=log_chunk,
            raw_response="{\"anomaly_score\": 0.9}",
        )

    monkeypatch.setattr(cli, "analyze_logs_ollama_chunk", fake_analyze)

    exit_code = cli.main(
        [
            "parse",
            str(tmp_log),
            "--prompt",
            str(prompt_file),
            "--model",
            "dummy-model",
            "--chunk-size",
            "5",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "⚠️" in output
    assert "🧠 Analyst Note" in output
    assert "📊 Session Statistics" in output
    assert "dummy-model" not in output  # ensure we don't echo internal parameters


def test_cli_parse_outputs_json(monkeypatch, capsys, tmp_log, prompt_file):
    def fake_analyze(session_id, log_chunk, prompt_path, model):
        return SessionAnalysis(
            session_id=session_id,
            anomaly_score=0.5,
            analyst_note="Normal",
            evidence=log_chunk,
            raw_response="{}",
        )

    monkeypatch.setattr(cli, "analyze_logs_ollama_chunk", fake_analyze)

    exit_code = cli.main(
        [
            "parse",
            str(tmp_log),
            "--prompt",
            str(prompt_file),
            "--output-format",
            "json",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert isinstance(payload, list)
    assert payload[0]["anomaly_score"] == 0.5
    assert "global_stats" in payload[0]
