"""Sidebar widget for browsing recent analyses."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class RecentAnalysesSidebar(QWidget):
    """Maintain a rolling cache of analysed sessions for comparison."""

    sessionSelected = Signal(object)

    def __init__(self, capacity: int = 10) -> None:
        super().__init__()
        self._capacity = max(1, capacity)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self._emit_selection)
        layout.addWidget(self.list_widget, 1)

    def add_session(self, processed: Any) -> None:
        payload = getattr(processed, "payload", processed)
        text = self._format_entry(payload)
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, processed)
        self.list_widget.insertItem(0, item)
        while self.list_widget.count() > self._capacity:
            self.list_widget.takeItem(self.list_widget.count() - 1)

    def _format_entry(self, payload: dict) -> str:
        session_id = payload.get("session_id", "—")
        score = payload.get("anomaly_score")
        score_text = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"
        return f"{session_id} • Score {score_text}"

    def _emit_selection(self, item: QListWidgetItem) -> None:
        session = item.data(Qt.UserRole)
        if session is not None:
            self.sessionSelected.emit(session)
