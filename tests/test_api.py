import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from watchpath import api
from watchpath.ai import SessionAnalysis

LOG_LINE = "192.168.1.30 - - [02/Mar/2025:12:00:00 +0000] \"GET /admin HTTP/1.1\" 200 512 \"-\" \"Mozilla/5.0\""


def test_parse_endpoint_returns_structured_payload(tmp_path, monkeypatch):
    log_file = tmp_path / "access.log"
    log_file.write_text(LOG_LINE + "\n")

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("You are a SOC analyst.")

    def fake_analyze(session_id: str, log_chunk: str, prompt_path: str, model: str) -> SessionAnalysis:
        return SessionAnalysis(
            session_id=session_id,
            anomaly_score=0.8,
            analyst_note="Suspicious admin access",
            evidence=log_chunk,
            raw_response=json.dumps({"anomaly_score": 0.8}),
        )

    monkeypatch.setattr(api, "_analyzer", fake_analyze)

    client = TestClient(api.app)
    response = client.post(
        "/parse",
        json={
            "log_path": str(log_file),
            "prompt_path": str(prompt_file),
            "include_text": True,
            "include_markdown": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "sessions" in payload
    assert payload["sessions"][0]["formats"]["markdown"].startswith("### Session")
    assert payload["global_stats"]["ip_distribution"] == {"192.168.1.30": 1}
