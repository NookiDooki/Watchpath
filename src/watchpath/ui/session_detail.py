"""Detailed session storytelling widgets."""

from __future__ import annotations

import difflib
import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from PySide6.QtCore import QByteArray, QSettings, Qt, QTimer, Signal
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
    QMenu,
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
    version: int
    timestamp: datetime


class SearchableTextBrowser(QTextBrowser):
    """Text browser with built-in highlighting support."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_term: str = ""
        self._highlight_positions: List[tuple[int, int]] = []
        self._current_index: int = -1

    def highlight(self, term: str) -> int:
        if not term:
            self._current_term = ""
            self._highlight_positions = []
            self._current_index = -1
            self.setExtraSelections([])
            return 0

        document: QTextDocument = self.document()
        highlight_format = self._build_format()

        cursor = QTextCursor(document)
        cursor.beginEditBlock()

        extra_selections: List[QTextEdit.ExtraSelection] = []
        positions: List[tuple[int, int]] = []
        while True:
            cursor = document.find(term, cursor)
            if cursor.isNull():
                break
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = highlight_format
            extra_selections.append(selection)
            positions.append((cursor.selectionStart(), cursor.selectionEnd()))
        cursor.endEditBlock()

        self.setExtraSelections(extra_selections)
        self._current_term = term
        self._highlight_positions = positions
        self._current_index = 0 if positions else -1
        if positions:
            self._focus_current_highlight()
        return len(positions)

    def next_highlight(self) -> None:
        if not self._highlight_positions:
            return
        self._current_index = (self._current_index + 1) % len(self._highlight_positions)
        self._focus_current_highlight()

    def previous_highlight(self) -> None:
        if not self._highlight_positions:
            return
        self._current_index = (self._current_index - 1) % len(self._highlight_positions)
        self._focus_current_highlight()

    def has_highlights(self) -> bool:
        return bool(self._highlight_positions)

    def _focus_current_highlight(self) -> None:
        if not self._highlight_positions or self._current_index < 0:
            return
        start, end = self._highlight_positions[self._current_index]
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    @staticmethod
    def _build_format():
        fmt = QTextEdit().currentCharFormat()
        fmt.setBackground(QColor(255, 235, 153))
        return fmt


class SessionDetailWidget(QWidget):
    """Display the details of a processed session with interactive tools."""

    noteUpdated = Signal(str, object)

    # Widgets created during initialisation. Declared up-front for clarity and to
    # guard against attribute-order regressions when the layout is refactored.
    evidence_view: SearchableTextBrowser
    logs_view: SearchableTextBrowser
    markdown_view: SearchableTextBrowser
    evidence_search: QLineEdit
    evidence_prev: QToolButton
    evidence_next: QToolButton
    logs_search: QLineEdit
    logs_prev: QToolButton
    logs_next: QToolButton

    def __init__(self) -> None:
        super().__init__()
        self._current_session: Optional[Any] = None
        self._note_history: Dict[str, List[NoteState]] = {}
        self._global_timeline: List[tuple[str, int]] = []
        self._session_records: List[Dict[str, Any]] = []
        self._settings = QSettings("Watchpath", "SessionDetailWidget")

        self._save_feedback_timer = QTimer(self)
        self._save_feedback_timer.setSingleShot(True)
        self._save_feedback_timer.timeout.connect(self._clear_save_feedback)

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
        self.save_feedback = QLabel("")
        controls.addWidget(self.save_feedback)
        self.history_button = QToolButton()
        self.history_button.setText("History")
        self.history_button.setPopupMode(QToolButton.InstantPopup)
        self.history_menu = QMenu(self.history_button)
        self.history_button.setMenu(self.history_menu)
        self.history_button.setEnabled(False)
        controls.addWidget(self.history_button)
        controls.addStretch(1)
        note_row.addLayout(controls, 1)

        layout.addLayout(note_row)

        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.evidence_view = self._create_browser("EvidenceView")
        self.logs_view = self._create_browser("LogsView")
        self.markdown_view = self._create_browser("MarkdownView")

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        (
            self.evidence_search,
            self.evidence_prev,
            self.evidence_next,
        ) = self._create_search_controls("Search evidence…", self.evidence_view)
        for widget in (self.evidence_search, self.evidence_prev, self.evidence_next):
            search_row.addWidget(widget)

        (
            self.logs_search,
            self.logs_prev,
            self.logs_next,
        ) = self._create_search_controls("Search logs…", self.logs_view)
        for widget in (self.logs_search, self.logs_prev, self.logs_next):
            search_row.addWidget(widget)
        left_layout.addLayout(search_row)

        self.tabs = QTabWidget()
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

        self.splitter.addWidget(left_panel)

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

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Method"))
        self.method_filter = QComboBox()
        self.method_filter.addItem("All", None)
        self.method_filter.currentIndexChanged.connect(self._render_session_timeline)
        filter_row.addWidget(self.method_filter)
        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("Status"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("All", None)
        self.status_filter.currentIndexChanged.connect(self._render_session_timeline)
        filter_row.addWidget(self.status_filter)
        filter_row.addStretch(1)
        right_layout.addLayout(filter_row)

        self.timeline_table = QTableWidget()
        self.timeline_table.setSortingEnabled(True)
        right_layout.addWidget(self.timeline_table, 2)

        self.diff_view = QTextBrowser()
        self.diff_view.setOpenExternalLinks(True)

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
        diff_header.addWidget(self._build_export_controls("Diff", self.diff_view, rich=True))
        right_layout.addLayout(diff_header)

        right_layout.addWidget(self.diff_view, 1)

        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

        self.splitter.splitterMoved.connect(lambda *_: self._save_splitter_state())
        self.tabs.currentChanged.connect(self._save_tab_state)

        self._restore_ui_state()

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
        self.save_feedback.clear()
        self.history_menu.clear()
        self.history_button.setEnabled(False)
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

        session_id = payload.get("session_id")
        history = self._load_note_history(session_id, payload)
        if history:
            latest = history[-1]
            self.note_edit.setPlainText(latest.text)
            self.tags_edit.setText(latest.tags)
            index = self.assignee_combo.findText(latest.assignee)
            self.assignee_combo.setCurrentIndex(max(index, 0))
        else:
            self.note_edit.setPlainText(payload.get("analyst_note", ""))
            self.tags_edit.clear()
            self.assignee_combo.setCurrentIndex(0)
        self._refresh_history_menu(session_id)

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
        self._update_timeline_filters(records)
        self._refresh_timeline_view()

    def set_global_timeline(self, timeline: Iterable[tuple[str, int]]) -> None:
        self._global_timeline = list(timeline)
        self._refresh_timeline_view()

    def _refresh_timeline_view(self) -> None:
        session_selected = self.timeline_source.currentIndex() == 0
        self.method_filter.setEnabled(session_selected)
        self.status_filter.setEnabled(session_selected)
        if not session_selected:
            self._render_global_timeline()
        else:
            self._render_session_timeline()

    def _render_session_timeline(self) -> None:
        records = self._session_records
        method_value = self.method_filter.currentData()
        status_value = self.status_filter.currentData()
        filtered = []
        for record in records:
            method_match = method_value is None or record.get("method") == method_value
            status_str = str(record.get("status")) if record.get("status") is not None else ""
            status_match = status_value is None or status_str == status_value
            if method_match and status_match:
                filtered.append(record)
        self.timeline_table.clear()
        self.timeline_table.setColumnCount(5)
        self.timeline_table.setHorizontalHeaderLabels(
            ["Timestamp", "Method", "Path", "Status", "Size"]
        )
        self.timeline_table.setRowCount(len(filtered))
        for row, record in enumerate(filtered):
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

    def _update_timeline_filters(self, records: Sequence[Dict[str, Any]]) -> None:
        methods = sorted({record.get("method") for record in records if record.get("method")})
        statuses = sorted({str(record.get("status")) for record in records if record.get("status") is not None})

        self.method_filter.blockSignals(True)
        current_method = self.method_filter.currentData()
        self.method_filter.clear()
        self.method_filter.addItem("All", None)
        for method in methods:
            self.method_filter.addItem(method, method)
        method_index = self.method_filter.findData(current_method)
        if method_index == -1:
            method_index = 0
        self.method_filter.setCurrentIndex(method_index)
        self.method_filter.blockSignals(False)

        self.status_filter.blockSignals(True)
        current_status = self.status_filter.currentData()
        self.status_filter.clear()
        self.status_filter.addItem("All", None)
        for status in statuses:
            self.status_filter.addItem(status, status)
        status_index = self.status_filter.findData(current_status)
        if status_index == -1:
            status_index = 0
        self.status_filter.setCurrentIndex(status_index)
        self.status_filter.blockSignals(False)

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
        if not session_id:
            return
        history = self._note_history.setdefault(session_id, [])
        version = history[-1].version + 1 if history else 1
        timestamp = datetime.utcnow()
        state = NoteState(
            text=self.note_edit.toPlainText(),
            tags=self.tags_edit.text(),
            assignee=self.assignee_combo.currentText(),
            version=version,
            timestamp=timestamp,
        )
        history.append(state)
        payload["analyst_note"] = state.text
        metadata = payload.setdefault("metadata", {})
        metadata["tags"] = state.tags
        metadata["assignee"] = state.assignee
        history_payload = payload.setdefault("note_history", [])
        history_payload.append(
            {
                "version": state.version,
                "text": state.text,
                "tags": state.tags,
                "assignee": state.assignee,
                "timestamp": state.timestamp.isoformat(),
            }
        )
        self._refresh_history_menu(session_id)
        self.save_feedback.setText(
            f"Saved v{state.version} at {state.timestamp.strftime('%H:%M:%S')}"
        )
        self._save_feedback_timer.start(3000)
        self.noteUpdated.emit(session_id, state)

    def _update_diff(self) -> None:
        base = self._text_for_source(self.diff_base.currentText())
        compare = self._text_for_source(self.diff_compare.currentText())
        if base is None or compare is None:
            self.diff_view.setHtml("<p>Select sources to compare.</p>")
            return
        diff_html = self._render_diff_html(base, compare)
        self.diff_view.setHtml(diff_html)

    def _text_for_source(self, source: str) -> Optional[str]:
        if source == "Evidence":
            return self.evidence_view.toPlainText()
        if source == "Logs":
            return self.logs_view.toPlainText()
        if source == "Markdown":
            return self.markdown_view.toPlainText()
        return None

    def _render_diff_html(self, base: str, compare: str) -> str:
        base_lines = base.splitlines()
        compare_lines = compare.splitlines()
        diff_lines = list(difflib.ndiff(base_lines, compare_lines))
        if not diff_lines:
            return "<p>No content available for diff.</p>"

        style = (
            "<style>"
            ".diff-view{font-family:monospace;font-size:13px;}"
            ".diff-line{display:block;padding:2px 6px;margin:0;}"
            ".diff-add{background-color:#e6ffed;color:#22863a;}"
            ".diff-remove{background-color:#ffeef0;color:#b31d28;}"
            ".diff-context{color:#24292e;}"
            ".diff-summary{font-weight:bold;margin-bottom:6px;}"
            "</style>"
        )

        lines: List[str] = []
        has_changes = False
        for line in diff_lines:
            if line.startswith("? "):
                continue
            content = html.escape(line[2:])
            if line.startswith("+ "):
                has_changes = True
                lines.append(f'<span class="diff-line diff-add">+ {content}</span>')
            elif line.startswith("- "):
                has_changes = True
                lines.append(f'<span class="diff-line diff-remove">- {content}</span>')
            else:
                lines.append(f'<span class="diff-line diff-context">  {content}</span>')

        if not lines:
            return "<p>No differences detected.</p>"

        summary = "No differences detected." if not has_changes else "Diff between selections"
        body = "\n".join(lines)
        return (
            f"<div class='diff-view'>{style}<div class='diff-summary'>{summary}</div>"
            f"<pre>{body}</pre></div>"
        )

    def _on_search_changed(
        self,
        view: SearchableTextBrowser,
        prev_button: QToolButton,
        next_button: QToolButton,
        text: str,
    ) -> None:
        count = view.highlight(text)
        has_results = count > 0
        prev_button.setEnabled(has_results)
        next_button.setEnabled(has_results)

    def _load_note_history(
        self, session_id: Optional[str], payload: Dict[str, Any]
    ) -> List[NoteState]:
        if not session_id:
            return []
        stored_history = payload.get("note_history") or []
        history: List[NoteState]
        if stored_history:
            entries = sorted(stored_history, key=lambda item: item.get("version", 0))
            history = []
            for entry in entries:
                try:
                    version = int(entry.get("version", len(history) + 1))
                except (TypeError, ValueError):
                    version = len(history) + 1
                timestamp_str = entry.get("timestamp")
                try:
                    timestamp = (
                        datetime.fromisoformat(timestamp_str)
                        if timestamp_str
                        else datetime.utcnow()
                    )
                except ValueError:
                    timestamp = datetime.utcnow()
                history.append(
                    NoteState(
                        text=entry.get("text", ""),
                        tags=entry.get("tags", ""),
                        assignee=entry.get("assignee", "Unassigned"),
                        version=version,
                        timestamp=timestamp,
                    )
                )
            self._note_history[session_id] = history
        else:
            history = self._note_history.get(session_id, [])
            if not history:
                existing_note = payload.get("analyst_note", "")
                metadata = payload.get("metadata", {}) or {}
                tags = metadata.get("tags", "") or ""
                assignee = metadata.get("assignee", "Unassigned") or "Unassigned"
                if existing_note or tags or assignee not in {"", "Unassigned"}:
                    history = [
                        NoteState(
                            text=existing_note,
                            tags=tags,
                            assignee=assignee,
                            version=1,
                            timestamp=datetime.utcnow(),
                        )
                    ]
                    self._note_history[session_id] = history
                else:
                    self._note_history.setdefault(session_id, [])
        return self._note_history.get(session_id, [])

    def _refresh_history_menu(self, session_id: Optional[str]) -> None:
        self.history_menu.clear()
        if not session_id:
            self.history_button.setEnabled(False)
            return
        history = self._note_history.get(session_id, [])
        if not history:
            placeholder = self.history_menu.addAction("No revisions yet")
            placeholder.setEnabled(False)
            self.history_button.setEnabled(False)
            return
        for revision in reversed(history):
            label = (
                f"v{revision.version} — {revision.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            action = self.history_menu.addAction(label)
            action.triggered.connect(
                lambda _=False, rev=revision: self._apply_revision(rev)
            )
        self.history_button.setEnabled(True)

    def _apply_revision(self, revision: NoteState) -> None:
        self.note_edit.setPlainText(revision.text)
        self.tags_edit.setText(revision.tags)
        index = self.assignee_combo.findText(revision.assignee)
        self.assignee_combo.setCurrentIndex(max(index, 0))
        self.save_feedback.setText(f"Loaded v{revision.version}")
        self._save_feedback_timer.start(2000)

    def _clear_save_feedback(self) -> None:
        self.save_feedback.clear()

    def _save_splitter_state(self) -> None:
        self._settings.setValue("splitterState", self.splitter.saveState())

    def _save_tab_state(self, index: int) -> None:
        self._settings.setValue("currentTab", index)

    def _restore_ui_state(self) -> None:
        splitter_state = self._settings.value("splitterState", QByteArray(), QByteArray)
        if isinstance(splitter_state, QByteArray) and not splitter_state.isEmpty():
            self.splitter.restoreState(splitter_state)
        tab_index = self._settings.value("currentTab", 0, int)
        if isinstance(tab_index, int) and 0 <= tab_index < self.tabs.count():
            self.tabs.setCurrentIndex(tab_index)

    def _create_browser(self, object_name: str) -> SearchableTextBrowser:
        browser = SearchableTextBrowser()
        browser.setObjectName(object_name)
        return browser

    def _create_search_controls(
        self, placeholder: str, view: SearchableTextBrowser
    ) -> tuple[QLineEdit, QToolButton, QToolButton]:
        search = QLineEdit()
        search.setPlaceholderText(placeholder)

        prev_button = QToolButton()
        prev_button.setText("‹")
        prev_button.setEnabled(False)
        prev_button.clicked.connect(view.previous_highlight)

        next_button = QToolButton()
        next_button.setText("›")
        next_button.setEnabled(False)
        next_button.clicked.connect(view.next_highlight)

        search.textChanged.connect(
            lambda text: self._on_search_changed(view, prev_button, next_button, text)
        )

        return search, prev_button, next_button

    def _build_export_controls(
        self, label: str, widget: Optional[QTextBrowser], *, rich: bool = False
    ) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        export_button = QToolButton()
        export_button.setText(f"Export {label}")
        export_button.clicked.connect(
            lambda: self._export_text(
                label,
                (widget.toHtml() if rich and widget else widget.toPlainText()) if widget else "",
                rich=rich,
            )
        )
        layout.addWidget(export_button)

        copy_button = QToolButton()
        copy_button.setText("Copy")
        copy_button.clicked.connect(
            lambda: self._copy_text(
                (widget.toHtml() if rich and widget else widget.toPlainText()) if widget else "",
                rich=rich,
            )
        )
        layout.addWidget(copy_button)

        return container

    def _export_text(self, label: str, text: str, *, rich: bool = False) -> None:
        if not text:
            return
        suffix = "html" if rich else "txt"
        path = Path.home() / f"watchpath_{label.lower()}.{suffix}"
        path.write_text(text)

    def _copy_text(self, text: str, *, rich: bool = False) -> None:
        if not text:
            return
        clipboard = QApplication.clipboard()
        if rich:
            clipboard.setHtml(text)
        else:
            clipboard.setText(text)

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
