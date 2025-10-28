"""PySide6 implementation of the kawaii Watchpath desktop experience."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QAction, QFont, QPalette, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QGraphicsOpacityEffect,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..ai import SessionAnalysis, analyze_logs_ollama_chunk
from ..parser import (
    Session,
    SessionStatistics,
    build_session_chunk,
    build_session_payload,
    format_session_markdown,
    format_session_report,
    load_sessions,
    summarize_sessions,
)

DEFAULT_PROMPT_PATH = Path("prompts/base_prompt.txt")

@dataclass(frozen=True)
class RiskVisual:
    """Visual configuration for a specific risk band."""

    text: str
    chunk_start: str
    chunk_end: str
    mascot: str
    background: str | None = None
    border: str | None = None


@dataclass(frozen=True)
class ScoreTheme:
    """Theme-driven styling for the Mochi meter."""

    background: str
    border: str
    text: str
    chunk_start: str
    chunk_end: str
    mascot: str
    risks: dict[str, RiskVisual]


DARK_STYLESHEET = """
QMainWindow { background: #101421; color: #edf1ff; }
QStatusBar { background: #151c2d; color: #c0cae5; border-top: 1px solid #222d42; }
QToolBar#MochiToolbar { background: #151c2d; border: 0; padding: 6px; spacing: 12px; }
#MochiToolbar QLabel { padding: 0 6px; font-weight: 600; color: #9fb3df; }
QPushButton, QComboBox, QSpinBox { background: #232d45; border: 1px solid #2f3b58; color: #edf1ff; border-radius: 8px; padding: 6px 10px; }
QPushButton:hover, QComboBox:hover, QSpinBox:hover { border-color: #5b8def; }
QPushButton:pressed { background: #1b2235; }
QComboBox QAbstractItemView { background: #151c2d; color: #edf1ff; selection-background-color: #2f3b58; }
QSlider::groove:horizontal { background: #232d45; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #5b8def; width: 18px; margin: -6px 0; border-radius: 9px; }
QSlider::sub-page:horizontal { background: #5b8def; }
#GlobalStats { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b2235, stop:1 #232d45); border-radius: 18px; border: 1px solid #2f3b58; }
#GlobalStatLabel, #GlobalStats QLabel { color: #c0cae5; }
#SessionCarousel { background: #151c2d; border-radius: 16px; padding: 12px; }
#SessionCarousel::item { background: #232d45; border-radius: 18px; padding: 14px; margin: 6px; color: #edf1ff; border: 1px solid #2f3b58; }
#SessionCarousel::item:selected { background: #2f3b58; border: 1px solid #5b8def; }
#SessionStatsCard { background: #1b2235; border-radius: 20px; padding: 18px; border: 1px solid #2f3b58; }
#AnalystNote { background: #151c2d; border-radius: 20px; padding: 18px; border: 1px dashed #2f3b58; color: #c0cae5; }
#SessionTabs::pane { border: 0; }
#SessionTabs::tab-bar { left: 12px; }
#SessionTabs::tab { background: #232d45; border-radius: 16px; padding: 8px 16px; margin-right: 8px; color: #c0cae5; border: 1px solid transparent; }
#SessionTabs::tab:selected { background: #2f3b58; color: #ffffff; border-color: #5b8def; }
QTextBrowser#EvidenceView, QTextBrowser#LogsView, QTextBrowser#MarkdownView { background: #151c2d; border-radius: 16px; padding: 12px; border: 1px solid #2f3b58; color: #edf1ff; }
QListWidget#SessionCarousel QScrollBar:vertical { background: #151c2d; width: 10px; }
QListWidget#SessionCarousel QScrollBar::handle:vertical { background: #2f3b58; border-radius: 5px; }
QListWidget#SessionCarousel QScrollBar::handle:vertical:hover { background: #5b8def; }
"""

LIGHT_STYLESHEET = """
QMainWindow { background: #f5f7fb; color: #1f2933; }
QStatusBar { background: #ffffff; color: #475569; border-top: 1px solid #d8def3; }
QToolBar#MochiToolbar { background: #ffffff; border: 0; padding: 6px; spacing: 12px; }
#MochiToolbar QLabel { padding: 0 6px; font-weight: 600; color: #6b7cc9; }
QPushButton, QComboBox, QSpinBox { background: #ffffff; border: 1px solid #d0d7ee; color: #1f2933; border-radius: 8px; padding: 6px 10px; }
QPushButton:hover, QComboBox:hover, QSpinBox:hover { border-color: #4c6ef5; }
QPushButton:pressed { background: #e9edfb; }
QComboBox QAbstractItemView { background: #ffffff; color: #1f2933; selection-background-color: #e1e7fb; }
QSlider::groove:horizontal { background: #d0d7ee; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #4c6ef5; width: 18px; margin: -6px 0; border-radius: 9px; }
QSlider::sub-page:horizontal { background: #4c6ef5; }
#GlobalStats { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #e8ecfb); border-radius: 18px; border: 1px solid #d0d7ee; }
#GlobalStatLabel, #GlobalStats QLabel { color: #475569; }
#SessionCarousel { background: #ffffff; border-radius: 16px; padding: 12px; }
#SessionCarousel::item { background: #f1f4ff; border-radius: 18px; padding: 14px; margin: 6px; color: #1f2933; border: 1px solid #d0d7ee; }
#SessionCarousel::item:selected { background: #dde4ff; border: 1px solid #4c6ef5; }
#SessionStatsCard { background: #ffffff; border-radius: 20px; padding: 18px; border: 1px solid #d0d7ee; }
#AnalystNote { background: #ffffff; border-radius: 20px; padding: 18px; border: 1px dashed #c3cefa; color: #475569; }
#SessionTabs::pane { border: 0; }
#SessionTabs::tab-bar { left: 12px; }
#SessionTabs::tab { background: #e7ebfb; border-radius: 16px; padding: 8px 16px; margin-right: 8px; color: #475569; border: 1px solid transparent; }
#SessionTabs::tab:selected { background: #4c6ef5; color: #f8fafc; border-color: #4c6ef5; }
QTextBrowser#EvidenceView, QTextBrowser#LogsView, QTextBrowser#MarkdownView { background: #ffffff; border-radius: 16px; padding: 12px; border: 1px solid #d0d7ee; color: #1f2933; }
QListWidget#SessionCarousel QScrollBar:vertical { background: #ffffff; width: 10px; }
QListWidget#SessionCarousel QScrollBar::handle:vertical { background: #c3cefa; border-radius: 5px; }
QListWidget#SessionCarousel QScrollBar::handle:vertical:hover { background: #4c6ef5; }
"""

THEME_CONFIGS = {
    "dark": {
        "palette": {
            QPalette.Window: "#101421",
            QPalette.WindowText: "#edf1ff",
            QPalette.Base: "#1b2235",
            QPalette.AlternateBase: "#232d45",
            QPalette.Text: "#edf1ff",
            QPalette.Button: "#232d45",
            QPalette.ButtonText: "#edf1ff",
            QPalette.Highlight: "#5b8def",
            QPalette.HighlightedText: "#0b101c",
            QPalette.ToolTipBase: "#232d45",
            QPalette.ToolTipText: "#edf1ff",
            QPalette.BrightText: "#ff9ad6",
        },
        "stylesheet": DARK_STYLESHEET,
        "score_theme": ScoreTheme(
            background="#151c2d",
            border="#2f3b58",
            text="#edf1ff",
            chunk_start="#5b8def",
            chunk_end="#70c1ff",
            mascot="#ffe6ff",
            risks={
                "safe": RiskVisual(
                    text="#34d399",
                    chunk_start="#0f766e",
                    chunk_end="#34d399",
                    mascot="#34d399",
                ),
                "low": RiskVisual(
                    text="#facc15",
                    chunk_start="#b45309",
                    chunk_end="#facc15",
                    mascot="#facc15",
                ),
                "medium": RiskVisual(
                    text="#fb923c",
                    chunk_start="#b43403",
                    chunk_end="#fb923c",
                    mascot="#fb923c",
                ),
                "high": RiskVisual(
                    text="#f87171",
                    chunk_start="#dc2626",
                    chunk_end="#f87171",
                    mascot="#f87171",
                ),
            },
        ),
    },
    "light": {
        "palette": {
            QPalette.Window: "#f5f7fb",
            QPalette.WindowText: "#1f2933",
            QPalette.Base: "#ffffff",
            QPalette.AlternateBase: "#eef1fb",
            QPalette.Text: "#1f2933",
            QPalette.Button: "#ffffff",
            QPalette.ButtonText: "#1f2933",
            QPalette.Highlight: "#4c6ef5",
            QPalette.HighlightedText: "#f8fafc",
            QPalette.ToolTipBase: "#ffffff",
            QPalette.ToolTipText: "#1f2933",
            QPalette.BrightText: "#f97316",
        },
        "stylesheet": LIGHT_STYLESHEET,
        "score_theme": ScoreTheme(
            background="#ffffff",
            border="#d0d7ee",
            text="#1f2933",
            chunk_start="#4c6ef5",
            chunk_end="#70a1ff",
            mascot="#4c6ef5",
            risks={
                "safe": RiskVisual(
                    text="#047857",
                    chunk_start="#6ee7b7",
                    chunk_end="#22c55e",
                    mascot="#047857",
                ),
                "low": RiskVisual(
                    text="#b45309",
                    chunk_start="#fde68a",
                    chunk_end="#facc15",
                    mascot="#b45309",
                ),
                "medium": RiskVisual(
                    text="#c2410c",
                    chunk_start="#fed7aa",
                    chunk_end="#fb923c",
                    mascot="#c2410c",
                ),
                "high": RiskVisual(
                    text="#b91c1c",
                    chunk_start="#fecaca",
                    chunk_end="#f87171",
                    mascot="#b91c1c",
                ),
            },
        ),
    },
}


@dataclass
class ProcessedSession:
    """Payload delivered from the worker thread to the UI."""

    payload: dict
    text_report: str
    markdown_report: str


class AnalysisWorker(QObject):
    """Background worker that parses logs and runs anomaly analysis."""

    status = Signal(str)
    error = Signal(str)
    progress = Signal(int, int)
    global_stats_ready = Signal(dict)
    session_ready = Signal(ProcessedSession)
    finished = Signal()

    def __init__(
        self,
        log_path: Path,
        *,
        chunk_size: int,
        model: str,
        prompt_path: Path,
    ) -> None:
        super().__init__()
        self.log_path = log_path
        self.chunk_size = max(1, chunk_size)
        self.model = model
        self.prompt_path = prompt_path
        self._should_stop = False

    def run(self) -> None:  # pragma: no cover - requires Qt event loop
        try:
            if not self.log_path.exists():
                raise FileNotFoundError(f"Log file not found: {self.log_path}")
            if not self.prompt_path.exists():
                raise FileNotFoundError(f"Prompt template not found: {self.prompt_path}")

            self.status.emit("🌸 Preparing tea and parsing sessions...")
            sessions = load_sessions(str(self.log_path))
            if not sessions:
                raise RuntimeError("No sessions discovered in the selected log file.")

            stats = summarize_sessions(sessions)
            global_payload = self._build_global_payload(stats)
            self.global_stats_ready.emit(global_payload)

            total = len(sessions)
            for index, session in enumerate(sessions, start=1):
                if self._should_stop:
                    break
                self.progress.emit(index, total)
                self.status.emit(
                    f"🍡 Whispering with session {session.session_id} ({index}/{total})..."
                )

                processed = self._process_session(session, stats)
                self.session_ready.emit(processed)

            if self._should_stop:
                self.status.emit("⏹️ Session analysis stopped. Showing collected results so far.")
            else:
                self.status.emit("🎉 All sessions have been pampered!")
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    def request_stop(self) -> None:
        self._should_stop = True

    def _build_global_payload(self, stats: SessionStatistics) -> dict:
        top_ips = sorted(
            stats.ip_distribution.items(), key=lambda item: item[1], reverse=True
        )[:3]
        return {
            "mean_session_duration_seconds": stats.mean_session_duration,
            "ip_distribution": stats.ip_distribution,
            "request_counts": stats.request_counts,
            "top_ips": top_ips,
        }

    def _process_session(self, session: Session, stats: SessionStatistics) -> ProcessedSession:
        chunk_text = build_session_chunk(session, self.chunk_size)
        try:
            analysis = analyze_logs_ollama_chunk(
                session_id=session.session_id,
                log_chunk=chunk_text,
                prompt_path=str(self.prompt_path),
                model=self.model,
            )
        except Exception as exc:  # pragma: no cover - UI feedback path
            fallback_evidence = "\n".join(record.raw for record in session.records[: self.chunk_size])
            analysis = SessionAnalysis(
                session_id=session.session_id,
                anomaly_score=None,
                analyst_note=f"Analysis unavailable: {exc}",
                evidence=fallback_evidence or "No evidence captured.",
                raw_response=str(exc),
            )

        payload = build_session_payload(session, analysis, stats)
        text_report = format_session_report(session, analysis, stats)
        markdown_report = format_session_markdown(session, analysis, stats)
        payload.update(
            {
                "chunk_size": self.chunk_size,
                "model": self.model,
                "prompt_path": str(self.prompt_path),
            }
        )
        return ProcessedSession(payload=payload, text_report=text_report, markdown_report=markdown_report)


class MascotWidget(QLabel):
    """Adorable mascot that reacts to anomaly scores."""

    def __init__(self) -> None:
        super().__init__("ฅ^•ﻌ•^ฅ")
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("TanukiMascot")
        self._current_mood = "calm"
        font = self.font()
        font.setPointSize(26)
        self.setFont(font)

    def update_mood(self, score: Optional[float]) -> None:
        if score is None:
            mood = "curious"
        elif score >= 0.75:
            mood = "alarmed"
        elif score >= 0.4:
            mood = "concerned"
        else:
            mood = "calm"

        if mood == self._current_mood:
            return
        self._current_mood = mood
        faces = {
            "calm": "ฅ^•ﻌ•^ฅ",
            "concerned": "(๑•̀д•́๑)",
            "alarmed": "(⊙﹏⊙✿)",
            "curious": "(≧◡≦) ♡",
        }
        self.setText(faces.get(mood, "ฅ^•ﻌ•^ฅ"))


class GlobalStatsWidget(QFrame):
    """Dark-mode dashboard summarising overall log behaviour."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("GlobalStats")
        self._fade_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fade_effect)
        self._fade_animation = QPropertyAnimation(self._fade_effect, b"opacity", self)
        self._fade_animation.setDuration(400)
        self._fade_animation.setStartValue(0.3)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.InOutCubic)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.title_label = QLabel("📊 General statistics")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.mean_duration = QLabel("Mean session duration: —")
        self.method_summary = QLabel("Request blend: —")
        self.top_ips = QLabel("Frequent visitors: —")

        for label in (self.mean_duration, self.method_summary, self.top_ips):
            label.setWordWrap(True)
            label.setObjectName("GlobalStatLabel")
            layout.addWidget(label)

    def update_stats(self, stats: dict) -> None:
        self._fade_animation.stop()
        self._fade_effect.setOpacity(0.3)
        self._fade_animation.start()
        if not stats:
            self.mean_duration.setText("Mean session duration: —")
            self.method_summary.setText("Request blend: —")
            self.top_ips.setText("Frequent visitors: —")
            return

        mean_seconds = stats.get("mean_session_duration_seconds", 0.0)
        self.mean_duration.setText(
            f"Mean session duration: {self._format_duration(mean_seconds)}"
        )

        request_counts = stats.get("request_counts", {})
        request_parts = [
            f"{method} {count}" for method, count in sorted(request_counts.items())
        ] or ["No requests"]
        self.method_summary.setText(
            "Request blend: " + " | ".join(request_parts)
        )

        top_ips = stats.get("top_ips", [])
        if top_ips:
            top_parts = [f"{ip} ({count})" for ip, count in top_ips]
        else:
            top_parts = ["No regulars yet"]
        self.top_ips.setText("Frequent visitors: " + " • ".join(top_parts))

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {sec}s"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"


class SessionListWidget(QListWidget):
    """Carousel-style list of session cards."""

    def __init__(self) -> None:
        super().__init__()
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setSpacing(14)
        self.setWrapping(True)
        self.setUniformItemSizes(False)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setWordWrap(True)
        self.setObjectName("SessionCarousel")

    def add_session(self, processed: ProcessedSession) -> None:
        payload = processed.payload
        score = payload.get("anomaly_score")
        emoji = "🍡"
        if isinstance(score, (int, float)):
            if score >= 0.75:
                emoji = "🚨"
            elif score >= 0.4:
                emoji = "🍓"
            else:
                emoji = "🌈"
        text = (
            f"{emoji} {payload['session_id']}\n"
            f"Score: {score if score is not None else 'N/A'}\n"
            f"Requests: {payload['session_stats']['request_count']}"
        )
        item = QListWidgetItem(text)
        size = item.sizeHint()
        size.setWidth(int(size.width() * 1.6))
        size.setHeight(int(size.height() * 1.4))
        item.setSizeHint(size)
        item.setTextAlignment(Qt.AlignCenter)
        item.setData(Qt.UserRole, processed)
        self.addItem(item)
        if self.count() == 1:
            self.setCurrentItem(item)


class SessionDetailWidget(QWidget):
    """Detailed storytelling view for a processed session."""

    def __init__(self) -> None:
        super().__init__()
        self._fade_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fade_effect)
        self._fade_animation = QPropertyAnimation(self._fade_effect, b"opacity", self)
        self._fade_animation.setDuration(450)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.InOutCubic)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        self.session_label = QLabel("Pick a session to see its story ✨")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.session_label.setFont(font)
        header.addWidget(self.session_label)

        self.score_bar = QProgressBar()
        self.score_bar.setMaximum(100)
        self.score_bar.setMinimum(0)
        self.score_bar.setFormat("Mochi meter: 0.00% (Safe)")
        self.score_bar.setObjectName("ScoreBar")
        self.score_bar.setAlignment(Qt.AlignCenter)
        self.score_bar.setFixedHeight(28)
        max_label = "Mochi meter: 100.00% (Critical)"
        metrics = self.score_bar.fontMetrics()
        min_width = metrics.boundingRect(max_label).width()
        # Add a little padding so the text does not feel cramped.
        self.score_bar.setMinimumWidth(int(min_width * 1.25))
        self.score_bar.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self._score_theme: ScoreTheme | None = None
        self._current_risk_key = "safe"
        header.addWidget(self.score_bar, 0)

        self.mascot = MascotWidget()
        header.addWidget(self.mascot, 0)
        header.addStretch(1)
        layout.addLayout(header)

        stats_frame = QFrame()
        stats_frame.setObjectName("SessionStatsCard")
        stats_layout = QFormLayout(stats_frame)
        stats_layout.setLabelAlignment(Qt.AlignLeft)
        stats_layout.setFormAlignment(Qt.AlignLeft)
        stats_layout.setHorizontalSpacing(20)
        stats_layout.setVerticalSpacing(8)
        layout.addWidget(stats_frame)

        self.duration_label = QLabel("—")
        self.request_label = QLabel("—")
        self.unique_label = QLabel("—")
        self.methods_label = QLabel("—")
        stats_layout.addRow("Duration", self.duration_label)
        stats_layout.addRow("Requests", self.request_label)
        stats_layout.addRow("Unique paths", self.unique_label)
        stats_layout.addRow("Method mix", self.methods_label)

        self.note_browser = QTextBrowser()
        self.note_browser.setObjectName("AnalystNote")
        self.note_browser.setPlaceholderText("Analyst notes will sparkle here…")
        layout.addWidget(self.note_browser, 2)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SessionTabs")
        self.evidence_view = QTextBrowser()
        self.evidence_view.setObjectName("EvidenceView")
        self.logs_view = QTextBrowser()
        self.logs_view.setObjectName("LogsView")
        self.markdown_view = QTextBrowser()
        self.markdown_view.setObjectName("MarkdownView")
        self.tabs.addTab(self.evidence_view, "Evidence Storybook")
        self.tabs.addTab(self.logs_view, "Raw Log Scroll")
        self.tabs.addTab(self.markdown_view, "Markdown Report")
        layout.addWidget(self.tabs, 3)

        self._current_session: Optional[ProcessedSession] = None

    def clear(self) -> None:
        self._current_session = None
        self.session_label.setText("Pick a session to see its story ✨")
        self.score_bar.setValue(0)
        self.score_bar.setFormat("Mochi meter: 0.00% (Safe)")
        self._apply_risk_style("safe")
        self.duration_label.setText("—")
        self.request_label.setText("—")
        self.unique_label.setText("—")
        self.methods_label.setText("—")
        self.note_browser.clear()
        self.evidence_view.clear()
        self.logs_view.clear()
        self.markdown_view.clear()
        self.mascot.update_mood(None)

    def display_session(self, processed: ProcessedSession) -> None:
        self._current_session = processed
        self._fade_animation.stop()
        self._fade_effect.setOpacity(0.0)
        payload = processed.payload
        self.session_label.setText(f"Session {payload['session_id']} ✦ IP {payload['ip']}")

        score = payload.get("anomaly_score")
        self._update_score_display(score)
        self.mascot.update_mood(score if isinstance(score, (int, float)) else None)

        stats = payload["session_stats"]
        self.duration_label.setText(self._format_duration(stats["duration_seconds"]))
        self.request_label.setText(str(stats["request_count"]))
        self.unique_label.setText(
            f"{stats['unique_path_count']} paths"
        )
        method_counts = stats.get("method_counts", {})
        parts = [f"{method} {count}" for method, count in sorted(method_counts.items())]
        self.methods_label.setText(
            ", ".join(parts) if parts else "No requests"
        )

        note = payload.get("analyst_note", "No analyst note provided.")
        escaped_note = self._escape(note).replace("\n", "<br/>")
        self.note_browser.setHtml(
            f"<h3>🧠 Analyst Note</h3><p>{escaped_note}</p>"
        )

        evidence_items = payload.get("evidence")
        evidence_text = self._render_evidence(evidence_items)
        self.evidence_view.setHtml(evidence_text)

        raw_logs = "\n".join(payload.get("raw_logs", []))
        self.logs_view.setPlainText(raw_logs)
        self.markdown_view.setMarkdown(processed.markdown_report)
        self._fade_animation.start()

    def apply_theme(self, theme: ScoreTheme) -> None:
        """Refresh the Mochi meter styling to match the selected theme."""

        self._score_theme = theme
        # Re-apply the current risk style so the colors stay in sync.
        self._apply_risk_style(self._current_risk_key)

    def _update_score_display(self, score: Optional[float]) -> None:
        if isinstance(score, (int, float)) and math.isfinite(score):
            percent = max(0.0, min(score * 100.0, 100.0))
            label, risk_key = self._classify_risk(percent)
            self.score_bar.setValue(int(round(percent)))
            self.score_bar.setFormat(f"Mochi meter: {percent:.2f}% ({label})")
            self._apply_risk_style(risk_key)
        else:
            self.score_bar.setValue(0)
            self.score_bar.setFormat("Mochi meter: 0.00% (Safe)")
            self._apply_risk_style("safe")

    def _apply_risk_style(self, key: str) -> None:
        self._current_risk_key = key
        if self._score_theme is None:
            return

        theme = self._score_theme
        risk = theme.risks.get(key, theme.risks.get("safe"))
        if risk is None:
            risk = RiskVisual(
                text=theme.text,
                chunk_start=theme.chunk_start,
                chunk_end=theme.chunk_end,
                mascot=theme.mascot,
            )

        background = risk.background or theme.background
        border = risk.border or theme.border
        text_color = risk.text or theme.text
        chunk_start = risk.chunk_start or theme.chunk_start
        chunk_end = risk.chunk_end or theme.chunk_end
        mascot_color = risk.mascot or theme.mascot

        self.score_bar.setStyleSheet(
            " ".join(
                [
                    (
                        "QProgressBar { "
                        f"border: 1px solid {border}; "
                        "border-radius: 14px; text-align: center; "
                        f"background: {background}; color: {text_color}; padding: 0 20px; }}"
                    ),
                    (
                        "QProgressBar::chunk { "
                        "border-radius: 12px; "
                        "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                        f"stop:0 {chunk_start}, stop:1 {chunk_end}); }}"
                    ),
                ]
            )
        )
        self.mascot.setStyleSheet(f"padding: 0 12px; color: {mascot_color};")

    @staticmethod
    def _classify_risk(percent: float) -> tuple[str, str]:
        if percent <= 0:
            return "Safe", "safe"
        if percent <= 10:
            return "Caution", "low"
        if percent < 60:
            # Treat anything above 10 up to 60 as elevated attention.
            return "Elevated", "medium"
        return "Critical", "high"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {sec}s"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _render_evidence(evidence: object) -> str:
        if evidence is None:
            return "<p>No evidence shared.</p>"
        if isinstance(evidence, str):
            escaped = SessionDetailWidget._escape(evidence)
            lines = "<br/>".join(escaped.splitlines())
            return f"<p>✨ {lines}</p>"
        if isinstance(evidence, Iterable):
            items = []
            for item in evidence:
                items.append(SessionDetailWidget._render_evidence(item))
            return "".join(items)
        escaped = SessionDetailWidget._escape(str(evidence))
        return f"<p>✨ {escaped}</p>"


class KawaiiMainWindow(QMainWindow):
    """Main window orchestrating the kawaii Watchpath GUI."""

    def __init__(
        self,
        *,
        default_model: str,
        default_chunk_size: int,
        default_prompt_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Watchpath Mochi Observatory")
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self._thread: Optional[QThread] = None
        self._worker: Optional[AnalysisWorker] = None

        self._processed_sessions: list[ProcessedSession] = []

        self._default_prompt_path = default_prompt_path or DEFAULT_PROMPT_PATH

        self._theme = "dark"
        self._build_toolbar(default_model, default_chunk_size)
        self._build_status_bar()
        self._build_layout()
        self._apply_theme()

    # ----- UI construction -------------------------------------------------
    def _build_toolbar(self, default_model: str, default_chunk_size: int) -> None:
        toolbar = QToolBar("Mochi Controls")
        toolbar.setObjectName("MochiToolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = QAction("Open Log 🍡", self)
        open_action.triggered.connect(self._choose_log_file)
        toolbar.addAction(open_action)

        self.stop_button = QPushButton("Stop ⏹")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._request_stop_analysis)
        toolbar.addWidget(self.stop_button)

        self.model_combo = QComboBox()
        self.model_combo.addItems(
            [
                default_model,
                "llama3:8b-instruct",
                "phi3:mini",
                "gemma:7b",
            ]
        )
        self.model_combo.setEditable(True)
        toolbar.addWidget(QLabel("Model"))
        toolbar.addWidget(self.model_combo)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(10, 500)
        self.chunk_spin.setValue(max(1, default_chunk_size))
        toolbar.addWidget(QLabel("Chunk size"))
        toolbar.addWidget(self.chunk_spin)

        self.prompt_button = QPushButton("Prompt ✨")
        self.prompt_button.clicked.connect(self._choose_prompt_template)
        toolbar.addWidget(self.prompt_button)

        toolbar.addSeparator()
        self.vibe_slider = QSlider(Qt.Horizontal)
        self.vibe_slider.setRange(0, 100)
        self.vibe_slider.setValue(50)
        self.vibe_slider.setToolTip(
            "Set the minimum anomaly score to display. Slide right to focus on higher-risk sessions."
        )
        self.vibe_slider.valueChanged.connect(self._apply_vibe_filter)
        toolbar.addWidget(QLabel("Anomaly threshold"))
        toolbar.addWidget(self.vibe_slider)

        toolbar.addSeparator()
        self.theme_button = QPushButton("☀️ Light mode")
        self.theme_button.clicked.connect(self._toggle_theme)
        self.theme_button.setToolTip("Switch between light and dark vibes")
        toolbar.addWidget(self.theme_button)

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        status.addPermanentWidget(self.progress_bar)
        self.setStatusBar(status)

    def _build_layout(self) -> None:
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(12, 12, 12, 12)
        central_layout.setSpacing(12)

        self.global_widget = GlobalStatsWidget()
        central_layout.addWidget(self.global_widget, 0)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        central_layout.addWidget(splitter, 1)

        self.session_list = SessionListWidget()
        self.session_list.itemSelectionChanged.connect(self._handle_session_selected)
        splitter.addWidget(self.session_list)

        self.detail_widget = SessionDetailWidget()
        splitter.addWidget(self.detail_widget)

        self.setCentralWidget(central)

    def _apply_theme(self) -> None:
        theme = THEME_CONFIGS[self._theme]
        palette = QPalette()
        for role, color in theme["palette"].items():
            palette.setColor(role, QColor(color))
        self.setPalette(palette)

        self.setStyleSheet(theme["stylesheet"])
        self.detail_widget.apply_theme(theme["score_theme"])
        if hasattr(self, "theme_button"):
            self.theme_button.setText(
                "🌙 Dark mode" if self._theme == "light" else "☀️ Light mode"
            )

    def _toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        self._apply_theme()
    # ----- Actions ---------------------------------------------------------
    def _choose_log_file(self) -> None:
        dialog = QFileDialog(self, "Choose a log file", str(Path.cwd()), "Log files (*.log *.txt);;All files (*)")
        if dialog.exec():
            selected = dialog.selectedFiles()
            if selected:
                self.load_log_file(Path(selected[0]))

    def _choose_prompt_template(self) -> None:
        dialog = QFileDialog(
            self,
            "Choose an Ollama prompt template",
            str(self._default_prompt_path.parent),
            "Text files (*.txt);;All files (*)",
        )
        if dialog.exec():
            selected = dialog.selectedFiles()
            if selected:
                self._default_prompt_path = Path(selected[0])
                self.statusBar().showMessage(
                    f"Prompt enchanted: {self._default_prompt_path}", 5000
                )

    def _apply_vibe_filter(self) -> None:
        if not self._processed_sessions:
            return
        threshold = self.vibe_slider.value() / 100
        for index in range(self.session_list.count()):
            item = self.session_list.item(index)
            processed: ProcessedSession = item.data(Qt.UserRole)
            score = processed.payload.get("anomaly_score")
            should_show = not isinstance(score, (int, float)) or score >= threshold
            item.setHidden(not should_show)
        self.statusBar().showMessage(
            f"Filtering for anomaly scores ≥ {threshold:.2f}", 3000
        )

    def load_log_file(self, path: Path) -> None:
        if self._thread and self._thread.isRunning():
            QMessageBox.warning(
                self,
                "Still brewing",
                "Please wait for the current analysis to finish before loading another log.",
            )
            return

        self._processed_sessions.clear()
        self.session_list.clear()
        self.detail_widget.clear()
        self.global_widget.update_stats({})

        chunk_size = self.chunk_spin.value()
        model = self.model_combo.currentText().strip() or "mistral:7b-instruct"
        prompt_path = self._default_prompt_path

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Summoning mochi spirits…")

        self.statusBar().showMessage(f"Opening {path}")

        self._thread = QThread(self)
        self._worker = AnalysisWorker(
            path,
            chunk_size=chunk_size,
            model=model,
            prompt_path=prompt_path,
        )
        self._worker.moveToThread(self._thread)

        self.stop_button.setEnabled(True)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._cleanup_thread)

        self._worker.status.connect(self.statusBar().showMessage)
        self._worker.error.connect(self._handle_worker_error)
        self._worker.progress.connect(self._update_progress)
        self._worker.global_stats_ready.connect(self._handle_global_stats)
        self._worker.session_ready.connect(self._handle_session_ready)

        self._thread.start()

    def _cleanup_thread(self) -> None:
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.stop_button.setEnabled(False)
        self._thread = None
        self._worker = None

    def _handle_worker_error(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)
        QMessageBox.critical(self, "Oh no!", message)

    def _update_progress(self, index: int, total: int) -> None:
        if total <= 0:
            self.progress_bar.setVisible(False)
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(index)
        self.progress_bar.setFormat(f"Session {index}/{total}")

    def _handle_global_stats(self, stats: dict) -> None:
        self.global_widget.update_stats(stats)

    def _handle_session_ready(self, processed: ProcessedSession) -> None:
        self._processed_sessions.append(processed)
        self.session_list.add_session(processed)

    def _request_stop_analysis(self) -> None:
        if not self._worker:
            return
        self.stop_button.setEnabled(False)
        self._worker.request_stop()
        self.progress_bar.setFormat("Stopping analysis…")
        self.statusBar().showMessage("Stopping analysis after current session…", 5000)

    def _handle_session_selected(self) -> None:
        item = self.session_list.currentItem()
        if not item:
            self.detail_widget.clear()
            return
        processed: ProcessedSession = item.data(Qt.UserRole)
        if processed:
            self.detail_widget.display_session(processed)

    # ----- Drag and drop ---------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # pragma: no cover - GUI behaviour
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # pragma: no cover - GUI behaviour
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.load_log_file(Path(url.toLocalFile()))
                break


__all__ = [
    "KawaiiMainWindow",
    "AnalysisWorker",
    "ProcessedSession",
]
