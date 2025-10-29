from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class SessionDetailWidget(QWidget):
    """Display the details of a processed session in a compact layout."""

    def __init__(self) -> None:
        super().__init__()
        self._current_session: Optional[Any] = None

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
        header.addWidget(self.session_label, 2)

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

        self.kaomoji_label = QLabel("(=^‥^=)")
        kaomoji_font = QFont()
        kaomoji_font.setPointSize(32)
        kaomoji_font.setBold(True)
        self.kaomoji_label.setFont(kaomoji_font)
        self.kaomoji_label.setAlignment(Qt.AlignCenter)
        stats_layout.addRow("Mochi mood", self.kaomoji_label)

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

        note_label = QLabel("Analyst note")
        layout.addWidget(note_label)
        self.note_display = QTextBrowser()
        self.note_display.setObjectName("AnalystNoteDisplay")
        self.note_display.setReadOnly(True)
        self.note_display.setPlaceholderText("No analyst note provided.")
        layout.addWidget(self.note_display)

        self.tabs = QTabWidget()
        self.evidence_view = QTextBrowser()
        self.evidence_view.setObjectName("EvidenceView")
        self.evidence_view.setOpenExternalLinks(True)
        self.logs_view = QTextBrowser()
        self.logs_view.setObjectName("LogsView")
        self.markdown_view = QTextBrowser()
        self.markdown_view.setObjectName("MarkdownView")

        self.tabs.addTab(self.evidence_view, "Evidence")
        self.tabs.addTab(self.logs_view, "Logs")
        self.tabs.addTab(self.markdown_view, "Markdown")

        layout.addWidget(self.tabs, 1)

        self._apply_severity_style(None)

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
        self.note_display.clear()
        self.evidence_view.clear()
        self.logs_view.clear()
        self.markdown_view.clear()
        self._apply_severity_style(None)

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
        self._apply_severity_style(score)

        stats = payload.get("session_stats", {})
        self.duration_label.setText(self._format_duration(stats.get("duration_seconds", 0.0)))
        self.request_label.setText(str(stats.get("request_count", "—")))
        self.unique_label.setText(str(stats.get("unique_path_count", "—")))
        method_counts = stats.get("method_counts", {})
        method_summary = ", ".join(
            f"{method} {count}" for method, count in sorted(method_counts.items())
        )
        self.method_label.setText(method_summary or "No requests")

        note = payload.get("analyst_note") or "No analyst note provided."
        self.note_display.setPlainText(note)

        evidence = payload.get("evidence")
        self.evidence_view.setPlainText(self._render_evidence_text(evidence))
        raw_logs = "\n".join(payload.get("raw_logs", []))
        self.logs_view.setPlainText(raw_logs)
        self.markdown_view.setMarkdown(getattr(processed, "markdown_report", ""))

    # ------------------------------------------------------------------
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

    def _apply_severity_style(self, score: Optional[float]) -> None:
        face, color = self._kaomoji_for_score(score)
        self.kaomoji_label.setText(face)
        self.kaomoji_label.setStyleSheet(
            f"color: {color}; text-shadow: 0 0 6px {color};"
        )

    @staticmethod
    def _kaomoji_for_score(score: Optional[float]) -> tuple[str, str]:
        if not isinstance(score, (int, float)):
            return "(=^‥^=)", "#65c466"
        if score < 0.25:
            return "(=^‥^=)ﾉ", "#65c466"
        if score < 0.5:
            return "(=^･ω･^=;)", "#f4b400"
        if score < 0.75:
            return "(=｀ェ´=)", "#fb8c00"
        return "(=；´ω`=)", "#e53935"

    @staticmethod
    def _format_duration(value: float) -> str:
        seconds = max(0.0, float(value or 0.0))
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{int(hours)}h {int(minutes)}m {int(sec)}s"
        if minutes:
            return f"{int(minutes)}m {int(sec)}s"
        return f"{int(sec)}s"

    @staticmethod
    def _render_evidence_text(evidence: Any) -> str:
        if evidence is None:
            return "No evidence captured."
        if isinstance(evidence, str):
            return evidence
        if isinstance(evidence, (bytes, bytearray)):
            try:
                return evidence.decode("utf-8")
            except Exception:
                return "(binary data)"
        if isinstance(evidence, list):
            return "\n".join(str(item) for item in evidence)
        return str(evidence)


__all__ = ["SessionDetailWidget"]

