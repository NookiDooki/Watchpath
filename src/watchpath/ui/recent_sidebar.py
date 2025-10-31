"""Sidebar widget for browsing recent analyses."""

from __future__ import annotations

from typing import Any, Iterable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from .severity import coerce_score, severity_for_score

# ╭──────────────────────────────────────────────────────────────╮
# │ Sidebar to revisit favourite sessions and comparisons.       │
# ╰──────────────────────────────────────────────────────────────╯


_PIN_ROLE = Qt.UserRole + 1


class RecentAnalysesSidebar(QWidget):
    """Maintain a rolling cache of analysed sessions for comparison."""

    sessionSelected = Signal(object)
    sessionPinned = Signal(object)
    compareRequested = Signal(object)
    detailRequested = Signal(object)

    def __init__(self, capacity: int = 10) -> None:
        super().__init__()
        self._capacity = max(1, capacity)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self._emit_selection)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, 1)

    def add_session(self, processed: Any) -> None:
        payload = getattr(processed, "payload", processed)
        text = self._format_entry(payload)
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, processed)
        item.setData(_PIN_ROLE, False)
        item.setToolTip(self._build_tooltip(payload))

        insert_row = self._pinned_count()
        self.list_widget.insertItem(insert_row, item)
        self._trim_to_capacity()

    # ╭──────────────────────────────────────────────────────────╮
    # │ Formatting helpers                                        │
    # ╰──────────────────────────────────────────────────────────╯
    def _format_entry(self, payload: dict) -> str:
        session_id = payload.get("session_id", "—")
        raw_score = payload.get("anomaly_score")
        score_value = coerce_score(raw_score)
        score = score_value if score_value is not None else 0.0
        style = severity_for_score(score)
        if score_value is None:
            score_text = "0.00"
        else:
            score_text = f"{score:.2f}"
        ip = payload.get("ip", "?")
        stats = payload.get("session_stats") or {}
        request_count = stats.get("request_count")
        request_text = f"{request_count} requests" if request_count is not None else "Requests: N/A"
        duration = stats.get("duration_seconds")
        duration_text = (
            f"{duration:.0f}s duration" if isinstance(duration, (int, float)) else "Duration: N/A"
        )
        label = "Score"
        if score_value is None:
            label = "Score (pending)"
        return (
            f"{session_id} • {label} {score_text}"
            f"\nIP {ip} • {request_text} • {duration_text}"
            f" • {style.label}"
        )

    def _build_tooltip(self, payload: dict) -> str:
        parts: list[str] = []
        summary = payload.get("summary")
        if summary:
            parts.append(str(summary))

        stats = payload.get("session_stats") or {}
        if stats:
            method_counts = stats.get("method_counts") or {}
            methods_text = ", ".join(
                f"{method}: {count}" for method, count in sorted(method_counts.items())
            )
            if methods_text:
                parts.append(f"Methods: {methods_text}")
            unique_paths = stats.get("unique_path_count")
            if unique_paths is not None:
                parts.append(f"Unique paths: {unique_paths}")

        evidence = payload.get("evidence")
        if evidence:
            parts.append(f"Evidence: {evidence}")

        return "\n".join(parts) if parts else "No additional metadata available."

    def _emit_selection(self, item: QListWidgetItem) -> None:
        session = item.data(Qt.UserRole)
        if session is not None:
            self.sessionSelected.emit(session)

    # ╭──────────────────────────────────────────────────────────╮
    # │ Context menu actions                                      │
    # ╰──────────────────────────────────────────────────────────╯
    def _show_context_menu(self, pos: QPoint) -> None:
        item = self.list_widget.itemAt(pos)
        if item is None:
            return

        session = item.data(Qt.UserRole)
        if session is None:
            return

        global_pos = self.list_widget.mapToGlobal(pos)
        menu = QMenu(self)

        pinned = bool(item.data(_PIN_ROLE))
        pin_action = QAction("Unpin from top" if pinned else "Pin to top", self)
        pin_action.triggered.connect(lambda: self._toggle_pin(item))
        menu.addAction(pin_action)

        compare_action = QAction("Compare with current", self)
        compare_action.triggered.connect(lambda: self._emit_compare(item))
        menu.addAction(compare_action)

        detail_action = QAction("Open in detail pane", self)
        detail_action.triggered.connect(lambda: self._open_details(item))
        menu.addAction(detail_action)

        menu.exec(global_pos)

    def _emit_compare(self, item: QListWidgetItem) -> None:
        session = item.data(Qt.UserRole)
        if session is not None:
            self.compareRequested.emit(session)

    def _open_details(self, item: QListWidgetItem) -> None:
        session = item.data(Qt.UserRole)
        if session is not None:
            self.detailRequested.emit(session)
            self.sessionSelected.emit(session)

    def _toggle_pin(self, item: QListWidgetItem) -> None:
        currently_pinned = bool(item.data(_PIN_ROLE))
        if currently_pinned:
            self._unpin_item(item)
        else:
            self._pin_item(item)

    def _pin_item(self, item: QListWidgetItem) -> None:
        session = item.data(Qt.UserRole)
        if session is None:
            return
        if bool(item.data(_PIN_ROLE)):
            return
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        item.setData(_PIN_ROLE, True)
        self.list_widget.insertItem(0, item)
        self.sessionPinned.emit(session)

    def _unpin_item(self, item: QListWidgetItem) -> None:
        if not bool(item.data(_PIN_ROLE)):
            return
        session = item.data(Qt.UserRole)
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        item.setData(_PIN_ROLE, False)
        insert_row = self._pinned_count()
        self.list_widget.insertItem(insert_row, item)
        if session is not None:
            self.sessionPinned.emit(session)

    def _pinned_count(self) -> int:
        return sum(1 for item in self._iter_items() if bool(item.data(_PIN_ROLE)))

    def _trim_to_capacity(self) -> None:
        while self.list_widget.count() > self._capacity:
            removed = False
            for row in range(self.list_widget.count() - 1, -1, -1):
                item = self.list_widget.item(row)
                if not bool(item.data(_PIN_ROLE)):
                    self.list_widget.takeItem(row)
                    removed = True
                    break
            if not removed:
                break

    def _iter_items(self) -> Iterable[QListWidgetItem]:
        return (self.list_widget.item(index) for index in range(self.list_widget.count()))
