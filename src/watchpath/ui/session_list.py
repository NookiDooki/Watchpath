"""Session carousel with advanced filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
)


@dataclass
class SessionListEntry:
    processed: Any
    session_id: str
    ip: str
    methods: Iterable[str]
    score: Optional[float]
    payload: Dict[str, Any]


class SessionListWidget(QWidget):
    """Carousel of sessions supporting multi-select and filters."""

    sessionActivated = Signal(object)
    selectionChanged = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self._entries: List[SessionListEntry] = []

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(6)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Quick search sessions…")
        self.search_box.textChanged.connect(self._apply_filters)
        layout.addWidget(self.search_box, 0, 0, 1, 2)

        self.method_filter = QComboBox()
        self.method_filter.addItem("All methods", None)
        self.method_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.method_filter, 0, 2)

        self.ip_filter = QComboBox()
        self.ip_filter.addItem("All IPs", None)
        self.ip_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.ip_filter, 0, 3)

        self.score_filter = QComboBox()
        self.score_filter.addItems(
            [
                "Any score",
                "High risk (≥ 0.75)",
                "Medium risk (0.4 – 0.74)",
                "Low risk (< 0.4)",
                "No score",
            ]
        )
        self.score_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.score_filter, 0, 4)

        self.clear_filters = QPushButton("Reset filters")
        self.clear_filters.clicked.connect(self._reset_filters)
        layout.addWidget(self.clear_filters, 0, 5)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(14)
        self.list_widget.setWrapping(True)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setWordWrap(True)
        self.list_widget.setObjectName("SessionCarousel")
        self.list_widget.itemSelectionChanged.connect(self._emit_selection)
        self.list_widget.itemDoubleClicked.connect(self._emit_activation)
        layout.addWidget(self.list_widget, 1, 0, 1, 6)

        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(4, 1)
        layout.setColumnStretch(5, 0)

    # ------------------------------------------------------------------
    def add_session(self, processed: Any) -> None:
        payload = getattr(processed, "payload", processed)
        session_id = payload.get("session_id", "unknown")
        ip = payload.get("ip", "-")
        methods = payload.get("session_stats", {}).get("method_counts", {}).keys()
        score = payload.get("anomaly_score")
        entry = SessionListEntry(
            processed=processed,
            session_id=session_id,
            ip=ip,
            methods=list(methods),
            score=score,
            payload=payload,
        )
        self._entries.append(entry)
        self._update_filters(entry)
        self._apply_filters()

    def clear(self) -> None:
        self._entries.clear()
        self.method_filter.clear()
        self.method_filter.addItem("All methods", None)
        self.ip_filter.clear()
        self.ip_filter.addItem("All IPs", None)
        self.list_widget.clear()

    def selected_payloads(self) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        for item in self.list_widget.selectedItems():
            entry = item.data(Qt.UserRole)
            if entry is not None:
                payloads.append(entry.payload)
        return payloads

    def selected_sessions(self) -> List[Any]:
        sessions: List[Any] = []
        for item in self.list_widget.selectedItems():
            entry = item.data(Qt.UserRole)
            if entry is not None:
                sessions.append(entry.processed)
        return sessions

    # ------------------------------------------------------------------
    def _reset_filters(self) -> None:
        self.search_box.clear()
        self.method_filter.setCurrentIndex(0)
        self.ip_filter.setCurrentIndex(0)
        self.score_filter.setCurrentIndex(0)

    def _update_filters(self, entry: SessionListEntry) -> None:
        def _ensure(combo: QComboBox, value: str, label_prefix: str) -> None:
            for index in range(combo.count()):
                if combo.itemData(index) == value:
                    return
            combo.addItem(f"{label_prefix}: {value}", value)

        for method in entry.methods:
            if method:
                _ensure(self.method_filter, method, "Method")
        if entry.ip:
            _ensure(self.ip_filter, entry.ip, "IP")

    def _passes_score_filter(self, score: Optional[float]) -> bool:
        index = self.score_filter.currentIndex()
        if index == 0:
            return True
        if index == 1:
            return isinstance(score, (int, float)) and score >= 0.75
        if index == 2:
            return isinstance(score, (int, float)) and 0.4 <= score < 0.75
        if index == 3:
            return isinstance(score, (int, float)) and score < 0.4
        if index == 4:
            return score is None
        return True

    def _apply_filters(self) -> None:
        query = self.search_box.text().strip().lower()
        method_value = self.method_filter.currentData()
        ip_value = self.ip_filter.currentData()

        self.list_widget.clear()
        font = QFont()
        font.setPointSize(10)

        for entry in self._entries:
            if query and query not in entry.session_id.lower():
                continue
            if method_value and method_value not in entry.methods:
                continue
            if ip_value and entry.ip != ip_value:
                continue
            if not self._passes_score_filter(entry.score):
                continue

            text_lines = [f"{entry.session_id}"]
            if entry.score is not None:
                text_lines.append(f"Score: {entry.score:.2f}")
            else:
                text_lines.append("Score: N/A")
            text_lines.append(f"IP: {entry.ip}")
            item = QListWidgetItem("\n".join(text_lines))
            item.setFont(font)
            size = item.sizeHint()
            size.setWidth(int(size.width() * 1.6))
            size.setHeight(int(size.height() * 1.6))
            item.setSizeHint(size)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, entry)
            self.list_widget.addItem(item)

        if self.list_widget.count() and not self.list_widget.selectedItems():
            self.list_widget.setCurrentRow(0)

    def _emit_selection(self) -> None:
        sessions = self.selected_sessions()
        self.selectionChanged.emit(sessions)

    def _emit_activation(self, item: QListWidgetItem) -> None:
        entry = item.data(Qt.UserRole)
        if entry:
            self.sessionActivated.emit(entry.processed)
