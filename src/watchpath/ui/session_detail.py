"""Detailed session storytelling widgets."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


@dataclass
class NoteState:
    text: str
    tags: str
    assignee: str


class SearchableTextBrowser(QTextBrowser):
    """Text browser with built-in highlighting support."""

    def highlight(self, term: str) -> None:
        if not term:
            self.setExtraSelections([])
            return
        document: QTextDocument = self.document()
        highlight_format = self._build_format()

        cursor = QTextCursor(document)
        cursor.beginEditBlock()

        extra_selections = []
        while True:
            cursor = document.find(term, cursor)
            if cursor.isNull():
                break
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = highlight_format
            extra_selections.append(selection)
        cursor.endEditBlock()
        self.setExtraSelections(extra_selections)

    @staticmethod
    def _build_format():
        fmt = QTextEdit().currentCharFormat()
        fmt.setBackground(QColor(255, 235, 153))
        return fmt


class SessionDetailWidget(QWidget):
    """Display the details of a processed session with interactive tools."""

    noteUpdated = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._current_session: Optional[Any] = None
        self._note_state: Dict[str, NoteState] = {}
        self._global_timeline: List[tuple[str, int]] = []
        self._session_records: List[Dict[str, Any]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.session_label = QLabel("Select a session to begin the journey ✨")
        header_font = QFont()
        header_font.setPointSize(20)
        header_font.setBold(True)
        self.session_label.setFont(header_font)
        header.addWidget(self.session_label, 1)

        self.metadata_label = QLabel("—")
        self.metadata_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.metadata_label, 1)

        layout.addLayout(header)

        stats_frame = QFrame()
        stats_frame.setObjectName("SessionStatsCard")
        stats_layout = QFormLayout(stats_frame)
        stats_layout.setLabelAlignment(Qt.AlignLeft)
        stats_layout.setHorizontalSpacing(20)
        stats_layout.setVerticalSpacing(8)

        self.score_label = QLabel("Mochi meter: 0.00% (Safe)")
        self.duration_label = QLabel("—")
        self.request_label = QLabel("—")
        self.unique_label = QLabel("—")
        self.method_label = QLabel("—")

        stats_layout.addRow("Score", self.score_label)
        stats_layout.addRow("Duration", self.duration_label)
        stats_layout.addRow("Requests", self.request_label)
        stats_layout.addRow("Unique paths", self.unique_label)
        stats_layout.addRow("Methods", self.method_label)

        layout.addWidget(stats_frame)

        note_row = QHBoxLayout()
        note_row.setSpacing(12)
        self.note_edit = QTextEdit()
        self.note_edit.setObjectName("AnalystNote")
        self.note_edit.setPlaceholderText("Record your observations…")
        note_row.addWidget(self.note_edit, 3)

        controls = QVBoxLayout()
        controls.setSpacing(6)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Tags (comma separated)")
        controls.addWidget(self.tags_edit)

        self.assignee_combo = QComboBox()
        self.assignee_combo.addItems(["Unassigned", "Network", "Application", "Security"])
        controls.addWidget(self.assignee_combo)

        self.save_note_button = QPushButton("Save note")
        self.save_note_button.clicked.connect(self._persist_note)
        controls.addWidget(self.save_note_button)
        controls.addStretch(1)
        note_row.addLayout(controls, 1)

        layout.addLayout(note_row)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.evidence_search = QLineEdit()
        self.evidence_search.setPlaceholderText("Search evidence…")
        self.evidence_search.textChanged.connect(self.evidence_view.highlight)
        search_row.addWidget(self.evidence_search)
        self.logs_search = QLineEdit()
        self.logs_search.setPlaceholderText("Search logs…")
        self.logs_search.textChanged.connect(self.logs_view.highlight)
        search_row.addWidget(self.logs_search)
        left_layout.addLayout(search_row)

        self.tabs = QTabWidget()
        self.evidence_view = SearchableTextBrowser()
        self.evidence_view.setObjectName("EvidenceView")
        self.logs_view = SearchableTextBrowser()
        self.logs_view.setObjectName("LogsView")
        self.markdown_view = SearchableTextBrowser()
        self.markdown_view.setObjectName("MarkdownView")
        self.tabs.addTab(self.evidence_view, "Evidence")
        self.tabs.addTab(self.logs_view, "Logs")
        self.tabs.addTab(self.markdown_view, "Markdown")

        export_row = QHBoxLayout()
        export_row.setSpacing(6)
        export_row.addWidget(self._build_export_controls("Evidence", self.evidence_view))
        export_row.addWidget(self._build_export_controls("Logs", self.logs_view))
        export_row.addWidget(self._build_export_controls("Markdown", self.markdown_view))
        left_layout.addLayout(export_row)

        left_layout.addWidget(self.tabs, 1)

        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        timeline_header = QHBoxLayout()
        timeline_header.addWidget(QLabel("Request timeline"))
        self.timeline_source = QComboBox()
        self.timeline_source.addItems(["Current session", "Global distribution"])
        self.timeline_source.currentIndexChanged.connect(self._refresh_timeline_view)
        timeline_header.addWidget(self.timeline_source)
        timeline_header.addStretch(1)
        right_layout.addLayout(timeline_header)

        self.timeline_table = QTableWidget()
        self.timeline_table.setSortingEnabled(True)
        right_layout.addWidget(self.timeline_table, 2)

        diff_header = QHBoxLayout()
        diff_header.addWidget(QLabel("Side-by-side diff"))
        self.diff_base = QComboBox()
        self.diff_compare = QComboBox()
        for combo in (self.diff_base, self.diff_compare):
            combo.addItems(["Evidence", "Logs", "Markdown"])
            combo.currentIndexChanged.connect(self._update_diff)
        diff_header.addWidget(self.diff_base)
        diff_header.addWidget(QLabel("vs"))
        diff_header.addWidget(self.diff_compare)
        right_layout.addLayout(diff_header)

        self.diff_view = QTextBrowser()
        self.diff_view.setOpenExternalLinks(True)
        right_layout.addWidget(self.diff_view, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self._current_session = None
        self.session_label.setText("Select a session to begin the journey ✨")
        self.metadata_label.setText("—")
        self.score_label.setText("Mochi meter: 0.00% (Safe)")
        self.duration_label.setText("—")
        self.request_label.setText("—")
        self.unique_label.setText("—")
        self.method_label.setText("—")
        self.note_edit.clear()
        self.tags_edit.clear()
        self.assignee_combo.setCurrentIndex(0)
        self.evidence_view.clear()
        self.logs_view.clear()
        self.markdown_view.clear()
        self.timeline_table.clearContents()
        self.timeline_table.setRowCount(0)
        self.diff_view.clear()

    def display_session(self, processed: Any) -> None:
        self._current_session = processed
        payload = getattr(processed, "payload", processed)

        header = f"Session {payload.get('session_id')} • IP {payload.get('ip')}"
        self.session_label.setText(header)

        metadata = []
        for key in ("model", "chunk_size", "prompt_path", "override_prompt_path"):
            value = payload.get(key)
            if value is not None:
                metadata.append(f"{key.replace('_', ' ').title()}: {value}")
        self.metadata_label.setText(" | ".join(metadata) if metadata else "—")

        score = payload.get("anomaly_score")
        score_text = "N/A"
        if isinstance(score, (int, float)):
            percent = min(max(float(score) * 100, 0.0), 100.0)
            score_text = f"{percent:.2f}%"
        label = self._classify_risk(score)
        self.score_label.setText(f"Mochi meter: {score_text} ({label})")

        stats = payload.get("session_stats", {})
        self.duration_label.setText(self._format_duration(stats.get("duration_seconds", 0.0)))
        self.request_label.setText(str(stats.get("request_count", "—")))
        self.unique_label.setText(str(stats.get("unique_path_count", "—")))
        method_counts = stats.get("method_counts", {})
        method_summary = ", ".join(f"{method} {count}" for method, count in sorted(method_counts.items()))
        self.method_label.setText(method_summary or "No requests")

        note_state = self._note_state.get(payload.get("session_id"))
        if note_state:
            self.note_edit.setPlainText(note_state.text)
            self.tags_edit.setText(note_state.tags)
            index = self.assignee_combo.findText(note_state.assignee)
            self.assignee_combo.setCurrentIndex(max(index, 0))
        else:
            self.note_edit.setPlainText(payload.get("analyst_note", ""))
            self.tags_edit.clear()
            self.assignee_combo.setCurrentIndex(0)

        evidence = payload.get("evidence")
        self.evidence_view.setHtml(self._render_evidence(evidence))
        raw_logs = "\n".join(payload.get("raw_logs", []))
        self.logs_view.setPlainText(raw_logs)
        self.markdown_view.setMarkdown(getattr(processed, "markdown_report", ""))

        self._populate_timeline(payload)
        self._update_diff()

    # ------------------------------------------------------------------
    def _populate_timeline(self, payload: Dict[str, Any]) -> None:
        records: Sequence[Dict[str, Any]] = list(payload.get("records", []) or [])
        self._session_records = list(records)
        self._refresh_timeline_view()

    def set_global_timeline(self, timeline: Iterable[tuple[str, int]]) -> None:
        self._global_timeline = list(timeline)
        self._refresh_timeline_view()

    def _refresh_timeline_view(self) -> None:
        if self.timeline_source.currentIndex() == 1:
            self._render_global_timeline()
        else:
            self._render_session_timeline()

    def _render_session_timeline(self) -> None:
        records = self._session_records
        self.timeline_table.clear()
        self.timeline_table.setColumnCount(5)
        self.timeline_table.setHorizontalHeaderLabels(
            ["Timestamp", "Method", "Path", "Status", "Size"]
        )
        self.timeline_table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.timeline_table.setItem(row, 0, QTableWidgetItem(record.get("timestamp", "")))
            self.timeline_table.setItem(row, 1, QTableWidgetItem(record.get("method", "")))
            self.timeline_table.setItem(row, 2, QTableWidgetItem(record.get("path", "")))
            self.timeline_table.setItem(row, 3, QTableWidgetItem(str(record.get("status", ""))))
            self.timeline_table.setItem(row, 4, QTableWidgetItem(str(record.get("size", ""))))
        self.timeline_table.resizeColumnsToContents()

    def _render_global_timeline(self) -> None:
        timeline = self._global_timeline
        self.timeline_table.clear()
        self.timeline_table.setColumnCount(2)
        self.timeline_table.setHorizontalHeaderLabels(["Bucket", "Requests"])
        self.timeline_table.setRowCount(len(timeline))
        for row, (bucket, count) in enumerate(timeline):
            self.timeline_table.setItem(row, 0, QTableWidgetItem(bucket))
            self.timeline_table.setItem(row, 1, QTableWidgetItem(str(count)))
        self.timeline_table.resizeColumnsToContents()

    def _render_evidence(self, evidence: Any) -> str:
        if evidence is None:
            return "<p>No evidence captured.</p>"
        if isinstance(evidence, str):
            escaped = evidence.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return "<p>✨ " + "<br/>".join(escaped.splitlines()) + "</p>"
        if isinstance(evidence, Iterable) and not isinstance(evidence, (bytes, bytearray, str)):
            return "".join(self._render_evidence(item) for item in evidence)
        return f"<p>✨ {evidence}</p>"

    def _persist_note(self) -> None:
        if not self._current_session:
            return
        payload = getattr(self._current_session, "payload", self._current_session)
        session_id = payload.get("session_id")
        state = NoteState(
            text=self.note_edit.toPlainText(),
            tags=self.tags_edit.text(),
            assignee=self.assignee_combo.currentText(),
        )
        self._note_state[session_id] = state
        payload["analyst_note"] = state.text
        payload.setdefault("metadata", {})["tags"] = state.tags
        payload["metadata"]["assignee"] = state.assignee
        self.noteUpdated.emit(session_id, state)

    def _update_diff(self) -> None:
        base = self._text_for_source(self.diff_base.currentText())
        compare = self._text_for_source(self.diff_compare.currentText())
        if base is None or compare is None:
            self.diff_view.setHtml("<p>Select sources to compare.</p>")
            return
        diff = difflib.unified_diff(
            base.splitlines(),
            compare.splitlines(),
            lineterm="",
            fromfile=self.diff_base.currentText(),
            tofile=self.diff_compare.currentText(),
        )
        diff_text = "\n".join(diff)
        if not diff_text.strip():
            diff_text = "No differences detected."
        self.diff_view.setPlainText(diff_text)

    def _text_for_source(self, source: str) -> Optional[str]:
        if source == "Evidence":
            return self.evidence_view.toPlainText()
        if source == "Logs":
            return self.logs_view.toPlainText()
        if source == "Markdown":
            return self.markdown_view.toPlainText()
        return None

    def _build_export_controls(self, label: str, widget: QTextBrowser) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        export_button = QToolButton()
        export_button.setText(f"Export {label}")
        export_button.clicked.connect(lambda: self._export_text(label, widget.toPlainText()))
        layout.addWidget(export_button)

        copy_button = QToolButton()
        copy_button.setText("Copy")
        copy_button.clicked.connect(lambda: self._copy_text(widget.toPlainText()))
        layout.addWidget(copy_button)

        return container

    def _export_text(self, label: str, text: str) -> None:
        if not text:
            return
        path = Path.home() / f"watchpath_{label.lower()}.txt"
        path.write_text(text)

    def _copy_text(self, text: str) -> None:
        if not text:
            return
        QApplication.clipboard().setText(text)

    @staticmethod
    def _classify_risk(score: Optional[float]) -> str:
        if not isinstance(score, (int, float)):
            return "Safe"
        percent = score * 100
        if percent < 10:
            return "Safe"
        if percent < 40:
            return "Caution"
        if percent < 75:
            return "Elevated"
        return "Critical"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {sec}s"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"
