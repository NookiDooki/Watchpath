import pytest

pytest.importorskip("PySide6")
try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable: {exc}", allow_module_level=True)

from watchpath.gui.main_window import ProcessedSession
from watchpath.parser import Session, SessionStatistics
from watchpath.ui import (
    GlobalStatsWidget,
    PromptManagerPanel,
    SessionDetailWidget,
    SessionListWidget,
)


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _build_processed(session_id: str) -> ProcessedSession:
    session = Session(session_id=session_id, ip="1.1.1.1", user="-", records=[])
    stats = SessionStatistics(
        mean_session_duration=0.0,
        ip_distribution={"1.1.1.1": 1},
        request_counts={"GET": 1},
        status_distribution={200: 1},
        request_timeline=[("2024-01-01T00:00:00", 1)],
    )
    payload = {
        "session_id": session_id,
        "ip": "1.1.1.1",
        "session_stats": {
            "duration_seconds": 0.0,
            "request_count": 1,
            "unique_path_count": 1,
            "method_counts": {"GET": 1},
        },
        "raw_logs": ["log"],
        "evidence": "evidence",
    }
    return ProcessedSession(
        session=session,
        global_stats=stats,
        payload=payload,
        text_report="",
        markdown_report="",
    )


def test_global_stats_widget_updates(qt_app):
    widget = GlobalStatsWidget()
    widget.update_stats(
        {
            "mean_session_duration_seconds": 42.0,
            "request_counts": {"GET": 3},
            "top_ips": [("1.1.1.1", 2)],
            "status_distribution": {200: 2},
            "request_timeline": [("2024-01-01T00:00:00", 1)],
        }
    )
    assert widget.chart_view.chart() is not None


def test_session_list_filters_and_selection(qt_app):
    widget = SessionListWidget()
    first = _build_processed("session-1")
    second = _build_processed("session-2")
    second.payload["session_stats"]["method_counts"] = {"POST": 2}
    widget.add_session(first)
    widget.add_session(second)

    widget.search_box.setText("session-2")
    assert widget.list_widget.count() == 1
    assert "session-2" in widget.list_widget.item(0).text()

    widget.search_box.setText("")
    widget.method_filter.setCurrentIndex(1)  # Filter by first method option
    assert widget.list_widget.count() >= 1


def test_prompt_manager_override_signal(tmp_path, qt_app):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    prompt_file = prompt_dir / "base.txt"
    prompt_file.write_text("Hello", encoding="utf-8")

    panel = PromptManagerPanel(prompt_root=prompt_dir)
    captured = []
    panel.overrideRequested.connect(lambda value: captured.append(value))
    panel.prompt_list.setCurrentRow(0)
    panel.override_button.click()
    assert captured and captured[0] == str(prompt_file)


def test_session_detail_updates_views_and_kaomoji(qt_app):
    widget = SessionDetailWidget()
    processed = _build_processed("session-3")
    processed.payload["analyst_note"] = "Check login sequence"
    processed.payload["anomaly_score"] = 0.8
    widget.display_session(processed)

    assert "Check login sequence" in widget.note_display.toPlainText()
    assert widget.evidence_view.toPlainText().strip() == "evidence"
    assert "session-3" in widget.session_label.text()
    assert "Critical" in widget.score_label.text()
    assert "(´" in widget.kaomoji_label.text()
