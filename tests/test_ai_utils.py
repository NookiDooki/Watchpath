from watchpath.ai import _enrich_analysis


LOG_CHUNK = (
    '2001:db8::abcd:1-9 - - [28/Oct/2025:00:00:02 +0000] "PUT /api/report HTTP/1.1" 400 2572 "-" "PostmanRuntime/7.32.2"\n'
    '2001:db8::abcd:1-9 - - [28/Oct/2025:00:00:02 +0000] "GET /socket.io/?EIO=4&transport=websocket HTTP/1.0" 101 0 "-" "Googlebot/2.1 (+http://www.google.com/bot.html)"\n'
    '2001:db8::abcd:1-9 - - [28/Oct/2025:00:00:02 +0000] "POST /login HTTP/1.1" 401 854 "https://app.example.com/login" "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"'
)  # noqa: E501


def test_enrich_analysis_generates_fallback_note_and_evidence():
    note, evidence = _enrich_analysis("95%", None, LOG_CHUNK)

    assert "error response" in note.lower()
    assert any("/login" in item for item in evidence)


def test_enrich_analysis_replaces_raw_log_evidence():
    note, evidence = _enrich_analysis("95%", [LOG_CHUNK], LOG_CHUNK)

    assert evidence != [LOG_CHUNK]
    assert evidence
