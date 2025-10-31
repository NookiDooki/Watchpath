"""Regression tests for the Watchpath main window interactions."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:  # pragma: no cover - optional dependency guard
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialogButtonBox
except ImportError as exc:  # pragma: no cover - test environment without Qt
    pytest.skip(f"PySide6 unavailable: {exc}", allow_module_level=True)

from watchpath.gui import main_window as main_window_mod
from watchpath.gui.main_window import KawaiiMainWindow
from watchpath.parser import LogRecord, Session


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _build_session(session_id: str, offset_minutes: int) -> Session:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    record = LogRecord(
        ip="1.1.1.1",
        ident="-",
        user="visitor",
        timestamp=base + timedelta(minutes=offset_minutes),
        method="GET",
        path="/",
        protocol="HTTP/1.1",
        status=200,
        size=123,
        referrer="-",
        user_agent="pytest",
        raw=f"raw-{session_id}",
    )
    return Session(session_id=session_id, ip="1.1.1.1", user="visitor", records=[record])


def test_load_log_shows_selection_dialog_and_applies_choice(qt_app, monkeypatch):
    window = KawaiiMainWindow(default_model="model", default_chunk_size=10)

    sessions = [
        _build_session("s-1", 0),
        _build_session("s-2", 5),
        _build_session("s-3", 10),
    ]

    monkeypatch.setattr(main_window_mod, "load_sessions", lambda path: sessions)

    captured: dict[str, object] = {}

    def fake_start_worker(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(window, "_start_worker", fake_start_worker)

    window.load_log_file(Path("dummy.log"))
    qt_app.processEvents()

    dialog = window._active_selection_dialog
    assert dialog is not None
    assert dialog.isVisible()

    dialog.count_spin.setValue(2)
    button_box = dialog.findChild(QDialogButtonBox)
    assert button_box is not None
    ok_button = button_box.button(QDialogButtonBox.Ok)
    assert ok_button is not None
    QTest.mouseClick(ok_button, Qt.LeftButton)
    qt_app.processEvents()

    assert captured["sessions"] == sessions[:2]
    assert captured["selection_summary"]
    assert window.status_label.text() == captured["selection_summary"]

    window.close()

