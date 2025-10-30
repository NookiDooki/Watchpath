"""Main window implementation for the Watchpath GUI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal, QDateTime, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
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
from ..ui import GlobalStatsWidget, PromptManagerPanel, SessionDetailWidget, SessionListWidget

DEFAULT_PROMPT_PATH = Path("prompts/base_prompt.txt")


@dataclass
class ProcessedSession:
    """Payload delivered from the worker thread to the UI."""

    session: Session
    global_stats: SessionStatistics
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
        selection_summary: str | None = None,
        sessions: list[Session] | None = None,
    ) -> None:
        super().__init__()
        self.log_path = log_path
        self.chunk_size = max(1, chunk_size)
        self.model = model
        self.prompt_path = prompt_path
        self._provided_sessions = list(sessions) if sessions is not None else None
        self._selection_summary = selection_summary
        self._should_stop = False

    def run(self) -> None:  # pragma: no cover - requires Qt event loop
        try:
            if not self.log_path.exists():
                raise FileNotFoundError(f"Log file not found: {self.log_path}")
            if not self.prompt_path.exists():
                raise FileNotFoundError(f"Prompt template not found: {self.prompt_path}")

            self.status.emit("🌸 Preparing tea and parsing sessions…")
            if self._provided_sessions is not None:
                sessions = list(self._provided_sessions)
                self._provided_sessions = None
            else:
                sessions = load_sessions(str(self.log_path))
            if not sessions:
                raise RuntimeError("No sessions discovered in the selected log file.")

            if self._selection_summary:
                self.status.emit(self._selection_summary)

            stats = summarize_sessions(sessions)
            self.global_stats_ready.emit(self._build_global_payload(stats))

            total = len(sessions)
            for index, session in enumerate(sessions, start=1):
                if self._should_stop:
                    break
                self.progress.emit(index, total)
                self.status.emit(
                    f"🍡 Whispering with session {session.session_id} ({index}/{total})…"
                )
                self.session_ready.emit(self._process_session(session, stats))

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
            "status_distribution": stats.status_distribution,
            "request_timeline": stats.request_timeline,
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
        return ProcessedSession(
            session=session,
            global_stats=stats,
            payload=payload,
            text_report=text_report,
            markdown_report=markdown_report,
        )


class RerunDialog(QDialog):
    """Dialog for selecting alternate analysis parameters."""

    def __init__(self, parent: Optional[QWidget], *, model: str, chunk_size: int, prompt: Path) -> None:
        super().__init__(parent)
        self.setWindowTitle("Re-run analysis")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.model_edit = QLineEdit(model)
        form.addRow("Model", self.model_edit)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setMinimum(1)
        self.chunk_spin.setMaximum(500)
        self.chunk_spin.setValue(chunk_size)
        form.addRow("Chunk size", self.chunk_spin)

        self.prompt_edit = QLineEdit(str(prompt))
        prompt_row = QHBoxLayout()
        prompt_row.addWidget(self.prompt_edit)
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._choose_prompt)
        prompt_row.addWidget(browse_button)
        form.addRow("Prompt", prompt_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_prompt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select prompt", "", "Text files (*.txt)")
        if path:
            self.prompt_edit.setText(path)

    def values(self) -> tuple[str, int, Path]:
        return (
            self.model_edit.text().strip(),
            int(self.chunk_spin.value()),
            Path(self.prompt_edit.text().strip()),
        )


class SessionSelectionDialog(QDialog):
    """Dialog allowing the user to pick which sessions should be analysed."""

    @staticmethod
    def _datetime_to_qdatetime(value: datetime) -> QDateTime:
        if hasattr(QDateTime, "fromPython"):
            return QDateTime.fromPython(value)
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
            spec = Qt.UTC
        else:
            spec = Qt.LocalTime
        return QDateTime(
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond // 1000,
            spec,
        )

    @staticmethod
    def _qdatetime_to_datetime(value: QDateTime) -> datetime:
        if hasattr(value, "toPython"):
            return value.toPython()
        # ``toMSecsSinceEpoch`` is available across Qt versions and keeps timezone info
        # via the returned epoch seconds. We normalise to UTC for consistent handling.
        milliseconds = value.toMSecsSinceEpoch()
        seconds, remainder = divmod(milliseconds, 1000)
        microseconds = remainder * 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
            microsecond=microseconds
        )

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def __init__(self, parent: Optional[QWidget], sessions: list[Session]) -> None:
        super().__init__(parent)
        self.setObjectName("SessionSelectionDialog")
        self.setWindowTitle("Choose sessions to inspect")
        self.setModal(True)
        self.resize(520, 420)

        self._sessions = sorted(
            sessions,
            key=lambda session: session.start
            or (datetime.min.replace(tzinfo=timezone.utc)),
        )
        self._selected_sessions: list[Session] = []
        self._selection_summary = ""

        total = len(self._sessions)
        earliest = self._sessions[0].start if self._sessions else None
        latest = self._sessions[-1].end if self._sessions else None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        summary = QLabel(
            f"🍰 We whisked together <b>{total}</b> delightful sessions from this log."
        )
        summary.setAlignment(Qt.AlignCenter)
        summary.setObjectName("SessionSummaryLabel")
        layout.addWidget(summary)

        hint = QLabel("Choose how many little stories you'd like to explore ✨")
        hint.setAlignment(Qt.AlignCenter)
        hint.setObjectName("SessionHintLabel")
        layout.addWidget(hint)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SessionTabs")
        layout.addWidget(self.tabs, 1)

        # Count based selection tab
        count_widget = QWidget()
        count_layout = QFormLayout(count_widget)
        count_layout.setContentsMargins(24, 24, 24, 24)
        count_layout.setSpacing(16)
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(max(1, total))
        self.count_spin.setValue(min(10, total))
        count_layout.addRow("Number of sessions", self.count_spin)

        self.count_preview = QLabel("")
        self.count_preview.setObjectName("SelectionPreview")
        count_layout.addRow("", self.count_preview)
        self.tabs.addTab(count_widget, "By count")

        # Time based selection tab
        time_widget = QWidget()
        time_layout = QFormLayout(time_widget)
        time_layout.setContentsMargins(24, 24, 24, 24)
        time_layout.setSpacing(16)

        self.start_edit = QDateTimeEdit()
        self.start_edit.setCalendarPopup(True)
        self.end_edit = QDateTimeEdit()
        self.end_edit.setCalendarPopup(True)

        if earliest:
            start_dt = self._datetime_to_qdatetime(earliest)
            self.start_edit.setDateTime(start_dt)
            self.start_edit.setMinimumDateTime(start_dt)
            if latest:
                self.start_edit.setMaximumDateTime(
                    self._datetime_to_qdatetime(latest)
                )
        else:
            self.start_edit.setEnabled(False)

        if latest:
            end_dt = self._datetime_to_qdatetime(latest)
            self.end_edit.setDateTime(end_dt)
            self.end_edit.setMaximumDateTime(end_dt)
            if earliest:
                self.end_edit.setMinimumDateTime(
                    self._datetime_to_qdatetime(earliest)
                )
        else:
            self.end_edit.setEnabled(False)

        self.start_edit.setDisplayFormat("dd MMM yyyy hh:mm")
        self.end_edit.setDisplayFormat("dd MMM yyyy hh:mm")

        time_layout.addRow("Start", self.start_edit)
        time_layout.addRow("End", self.end_edit)

        self.time_preview = QLabel("")
        self.time_preview.setObjectName("SelectionPreview")
        time_layout.addRow("", self.time_preview)
        self.tabs.addTab(time_widget, "By time")

        if not (earliest and latest):
            time_widget.setEnabled(False)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.count_spin.valueChanged.connect(self._update_count_preview)
        self.start_edit.dateTimeChanged.connect(self._update_time_preview)
        self.end_edit.dateTimeChanged.connect(self._update_time_preview)

        self._update_count_preview(self.count_spin.value())
        self._update_time_preview()
        self._apply_style(parent)

    def _apply_style(self, parent: Optional[QWidget]) -> None:
        theme = "dark"
        if parent and hasattr(parent, "theme_combo"):
            theme = parent.theme_combo.currentText()
        if theme == "light":
            bg = "#f7f4ff"
            text = "#1f1b2e"
            accent = "#7c3aed"
            card = "rgba(124, 58, 237, 0.08)"
        else:
            bg = "#111a2e"
            text = "#e2e8f0"
            accent = "#c084fc"
            card = "rgba(15, 23, 42, 0.65)"

        self.setStyleSheet(
            "QDialog#SessionSelectionDialog {"
            f" background-color: {bg};"
            " border-radius: 24px;"
            "}"
            "QLabel#SessionSummaryLabel, QLabel#SessionHintLabel {"
            f" color: {text};"
            " font-size: 16px;"
            " font-weight: 600;"
            "}"
            "QTabWidget::pane {"
            f" background: {card};"
            " border-radius: 18px;"
            f" border: 1px solid {accent};"
            " padding: 12px;"
            "}"
            "QTabBar::tab {"
            f" background: {card};"
            f" color: {text};"
            " border-radius: 16px;"
            " padding: 8px 18px;"
            " margin: 4px;"
            " font-weight: 600;"
            "}"
            "QTabBar::tab:selected {"
            f" background: {accent};"
            " color: white;"
            "}"
            "QLabel#SelectionPreview {"
            f" color: {text};"
            " font-style: italic;"
            "}" 
            "QDialogButtonBox QPushButton {"
            f" background: {accent};"
            " color: white;"
            " border-radius: 16px;"
            " padding: 8px 18px;"
            " font-weight: 600;"
            " min-width: 120px;"
            "}"
            "QDialogButtonBox QPushButton:disabled {"
            " background: #888;"
            " color: #eee;"
            "}"
        )

    def _update_count_preview(self, value: int) -> None:
        total = len(self._sessions)
        if total == 1:
            message = "The lone session will be reviewed."
        else:
            message = f"We'll pamper the first {value} of {total} sessions."
        self.count_preview.setText(message)

    def _update_time_preview(self) -> None:
        if not (self.start_edit.isEnabled() and self.end_edit.isEnabled()):
            self.time_preview.setText(
                "Time window selection isn't available for these sessions."
            )
            return

        start_dt = self.start_edit.dateTime()
        end_dt = self.end_edit.dateTime()
        if not start_dt.isValid() or not end_dt.isValid():
            self.time_preview.setText("Choose a valid time range to see matching sessions.")
            return
        if start_dt > end_dt:
            self.time_preview.setText("Start time must be before end time.")
            return

        start = self._qdatetime_to_datetime(start_dt)
        end = self._qdatetime_to_datetime(end_dt)

        matched = [
            session
            for session in self._sessions
            if self._session_overlaps(session, start, end)
        ]
        if matched:
            message = (
                f"This dreamy window wraps {len(matched)} session"
                f"{'s' if len(matched) != 1 else ''}."
            )
        else:
            message = "No sessions sparkle inside this window yet."
        self.time_preview.setText(message)

    @staticmethod
    def _session_overlaps(session: Session, start: datetime, end: datetime) -> bool:
        if not session.records:
            return False
        session_start = session.start or session.records[0].timestamp
        session_end = session.end or session.records[-1].timestamp
        start = SessionSelectionDialog._ensure_utc(start)
        end = SessionSelectionDialog._ensure_utc(end)
        session_start = SessionSelectionDialog._ensure_utc(session_start)
        session_end = SessionSelectionDialog._ensure_utc(session_end)
        return (session_end >= start) and (session_start <= end)

    def _on_accept(self) -> None:
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            limit = int(self.count_spin.value())
            self._selected_sessions = self._sessions[:limit]
            self._selection_summary = (
                f"🧁 Inspecting {limit} session{'s' if limit != 1 else ''} out of {len(self._sessions)}."
            )
            self.accept()
            return

        start_dt = self.start_edit.dateTime()
        end_dt = self.end_edit.dateTime()
        if not start_dt.isValid() or not end_dt.isValid():
            QMessageBox.warning(self, "Choose sessions", "Please provide a valid time range.")
            return
        if start_dt > end_dt:
            QMessageBox.warning(self, "Choose sessions", "Start time must be before end time.")
            return

        start = self._qdatetime_to_datetime(start_dt)
        end = self._qdatetime_to_datetime(end_dt)
        matches = [
            session
            for session in self._sessions
            if self._session_overlaps(session, start, end)
        ]
        if not matches:
            QMessageBox.information(
                self,
                "Choose sessions",
                "No sessions were discovered inside that time window. Try a wider hug!",
            )
            return
        self._selected_sessions = matches
        self._selection_summary = (
            f"🌙 Exploring {len(matches)} session"
            f"{'s' if len(matches) != 1 else ''} between {start:%d %b %Y %H:%M} and {end:%d %b %Y %H:%M}."
        )
        self.accept()

    def selected_sessions(self) -> list[Session]:
        return list(self._selected_sessions)

    def selection_summary(self) -> str:
        return self._selection_summary


class KawaiiMainWindow(QMainWindow):
    """Main window orchestrating the Watchpath GUI."""

    def __init__(
        self,
        *,
        default_model: str,
        default_chunk_size: int,
        default_prompt_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Watchpath Mochi Observatory")
        self.resize(1400, 860)
        self.setAcceptDrops(True)

        self._thread: Optional[QThread] = None
        self._worker: Optional[AnalysisWorker] = None

        self._processed_sessions: list[ProcessedSession] = []
        self._session_overrides: dict[str, Path] = {}
        self._last_log_path: Optional[Path] = None
        self._last_global_stats: dict = {}

        self._default_prompt_path = default_prompt_path or DEFAULT_PROMPT_PATH
        self._default_model = default_model
        self._default_chunk_size = default_chunk_size

        self._prompt_manager_dialog: QDialog | None = None
        self._prompt_manager_panel: PromptManagerPanel | None = None
        self._active_selection_dialog: SessionSelectionDialog | None = None

        self._toolbar: QToolBar | None = None
        self._stop_button: QToolButton | None = None

        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._build_layout()

    def _build_menus(self) -> None:
        menu = self.menuBar().addMenu("Tools")
        manager_action = menu.addAction("Model manager…")
        manager_action.triggered.connect(self._open_model_manager)

    # ------------------------------------------------------------------
    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Controls")
        toolbar.setObjectName("MochiToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)
        self._toolbar = toolbar

        def _make_button(label: str, emoji: str, handler) -> QToolButton:
            button = QToolButton()
            button.setObjectName("MochiToolbarButton")
            button.setText(f"{emoji} {label}")
            button.setCursor(Qt.PointingHandCursor)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setAutoRaise(True)
            button.clicked.connect(handler)
            return button

        toolbar.addWidget(_make_button("Choose log", "🍡", self._choose_log_file))
        toolbar.addWidget(
            _make_button("Change model and parameters", "⚙️", self._prompt_rerun)
        )

        self._stop_button = _make_button("Stop analysis", "🛑", self._stop_worker)
        self._stop_button.setEnabled(False)
        toolbar.addWidget(self._stop_button)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        theme_label = QLabel("Theme")
        theme_label.setObjectName("ToolbarLabel")
        toolbar.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("ThemeSelector")
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        toolbar.addWidget(self.theme_combo)

        self._refresh_toolbar_theme()

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.status_label = QLabel("Drop a log file to begin the adventure.")
        status.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setMinimum(0)
        self.progress.setVisible(False)
        status.addPermanentWidget(self.progress)
        self.setStatusBar(status)

    def _build_layout(self) -> None:
        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self.global_stats = GlobalStatsWidget()
        left_layout.addWidget(self.global_stats, 0)

        self.session_list = SessionListWidget()
        self.session_list.sessionActivated.connect(self._on_session_activated)
        self.session_list.selectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.session_list, 1)

        splitter.addWidget(left_panel)

        self.detail_widget = SessionDetailWidget()
        splitter.addWidget(self.detail_widget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([420, 880])

        self.setCentralWidget(central)
        self._apply_theme()

    # ------------------------------------------------------------------
    def _apply_theme(self) -> None:
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else "dark"
        app = QApplication.instance()
        if not app:
            return
        if theme == "light":
            base_bg = "#f8f5ff"
            text = "#1f2937"
            card_bg = "#ffffff"
            border = "#d8ccff"
            tile_bg = "#ede9fe"
        else:
            base_bg = "#0f172a"
            text = "#e2e8f0"
            card_bg = "#1e293b"
            border = "#334155"
            tile_bg = "#1b2536"

        app.setStyleSheet(
            "QMainWindow {"
            f" background: {base_bg};"
            f" color: {text};"
            "}"
            "QLabel {"
            f" color: {text};"
            "}"
            "QFrame#SessionStatsCard {"
            f" background-color: {card_bg};"
            " border-radius: 22px;"
            f" border: 1px solid {border};"
            "}"
            "QFrame#GlobalStats {"
            f" background-color: {card_bg};"
            " border-radius: 20px;"
            f" border: 1px solid {border};"
            "}"
            "QFrame#MetricTile {"
            f" background-color: {tile_bg};"
            " border-radius: 14px;"
            "}"
            "QLabel.MetricTileCaption {"
            f" color: {text};"
            "}")

        self._refresh_toolbar_theme()

    # ------------------------------------------------------------------
    def _refresh_toolbar_theme(self) -> None:
        if not self._toolbar:
            return

        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else "dark"
        if theme == "light":
            bar_bg = "#f1ecff"
            button_bg = "#ede9fe"
            button_hover = "#e0d7fe"
            text_color = "#1f1b2e"
            accent = "#7c3aed"
        else:
            bar_bg = "#131d32"
            button_bg = "#1b2536"
            button_hover = "#243049"
            text_color = "#e2e8f0"
            accent = "#c084fc"

        toolbar_style = (
            "QToolBar#MochiToolbar {"
            f" background: {bar_bg};"
            " border: none;"
            " padding: 6px 12px;"
            "}"
            "QToolBar#MochiToolbar QLabel#ToolbarLabel {"
            f" color: {text_color};"
            " font-weight: 600;"
            " margin-right: 6px;"
            "}"
            "QToolBar#MochiToolbar QToolButton#MochiToolbarButton {"
            f" background: {button_bg};"
            f" color: {text_color};"
            " border-radius: 18px;"
            " padding: 6px 14px;"
            " font-weight: 600;"
            "}"
            "QToolBar#MochiToolbar QToolButton#MochiToolbarButton:hover {"
            f" background: {button_hover};"
            "}"
            "QToolBar#MochiToolbar QToolButton#MochiToolbarButton:pressed {"
            f" background: {button_hover};"
            " opacity: 0.9;"
            "}"
            "QComboBox#ThemeSelector {"
            f" background: {button_bg};"
            f" color: {text_color};"
            f" border: 1px solid {accent};"
            " border-radius: 16px;"
            " padding: 4px 12px;"
            " min-width: 100px;"
            " font-weight: 600;"
            "}"
            "QComboBox#ThemeSelector::drop-down { border: 0px; }"
        )
        self._toolbar.setStyleSheet(toolbar_style)

        if hasattr(self, "theme_combo"):
            self.theme_combo.setStyleSheet("")

    # ------------------------------------------------------------------
    def _refresh_toolbar_state(self) -> None:
        if self._stop_button is not None:
            self._stop_button.setEnabled(self._worker is not None)

    # ------------------------------------------------------------------
    def _choose_log_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select access log",
            "",
            "Log files (*.log *.txt);;All files (*)",
        )
        if path:
            # Present the session selection dialog once the event loop regains
            # control. Showing a modal dialog immediately after the native
            # ``QFileDialog`` closes can prevent it from appearing on some
            # platforms.
            QTimer.singleShot(0, lambda: self.load_log_file(Path(path)))

    def load_log_file(self, path: Path) -> None:
        app = QApplication.instance()
        cursor_active = False
        if app is not None:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            cursor_active = True

        try:
            sessions = load_sessions(str(path))
        except Exception as exc:
            if cursor_active:
                QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Load log", str(exc))
            return

        if not sessions:
            if cursor_active:
                QApplication.restoreOverrideCursor()
            QMessageBox.information(
                self,
                "Load log",
                "No sessions discovered in this log file. Maybe try another mochi batch?",
            )
            return

        if cursor_active:
            QApplication.restoreOverrideCursor()

        self._show_session_selection_dialog(path, sessions)

    def _show_session_selection_dialog(
        self, path: Path, sessions: list[Session]
    ) -> None:
        if self._active_selection_dialog is not None:
            self._active_selection_dialog.close()
            self._active_selection_dialog.deleteLater()
            self._active_selection_dialog = None

        dialog = SessionSelectionDialog(self, sessions)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setWindowModality(Qt.ApplicationModal)

        def _on_dialog_finished(_result: int) -> None:
            if self._active_selection_dialog is dialog:
                self._active_selection_dialog = None

        def _on_dialog_accepted() -> None:
            selected_sessions = dialog.selected_sessions()
            if not selected_sessions:
                return
            self._finalise_log_selection(
                path, selected_sessions, dialog.selection_summary()
            )

        dialog.accepted.connect(_on_dialog_accepted)
        dialog.finished.connect(_on_dialog_finished)

        self._active_selection_dialog = dialog
        dialog.open()
        QTimer.singleShot(0, lambda: self._focus_dialog(dialog))

    def _focus_dialog(self, dialog: QDialog) -> None:
        if dialog is None:
            return
        if not dialog.isVisible():
            dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _finalise_log_selection(
        self, path: Path, sessions: list[Session], summary: str
    ) -> None:
        self._last_log_path = path
        self.session_list.clear()
        self.detail_widget.clear()
        self._processed_sessions.clear()
        self._session_overrides.clear()
        self.status_label.setText(summary)
        self._start_worker(
            log_path=path,
            model=self._default_model,
            chunk_size=self._default_chunk_size,
            prompt_path=self._default_prompt_path,
            selection_summary=summary,
            sessions=sessions,
        )

    def _start_worker(
        self,
        *,
        log_path: Path,
        model: str,
        chunk_size: int,
        prompt_path: Path,
        selection_summary: str | None = None,
        sessions: list[Session] | None = None,
    ) -> None:
        self._stop_worker()
        self.status_label.setText("🍡 Spinning up worker…")
        self.progress.setVisible(True)
        self.progress.setMaximum(0)

        self._thread = QThread()
        self._worker = AnalysisWorker(
            log_path=log_path,
            chunk_size=chunk_size,
            model=model,
            prompt_path=prompt_path,
            selection_summary=selection_summary,
            sessions=sessions,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.status.connect(self.status_label.setText)
        self._worker.error.connect(self._show_error)
        self._worker.progress.connect(self._update_progress)
        self._worker.session_ready.connect(self._add_processed_session)
        self._worker.global_stats_ready.connect(self._update_global_stats)
        self._worker.finished.connect(self._on_worker_finished)
        self._thread.start()
        self._refresh_toolbar_state()

    def _update_progress(self, index: int, total: int) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(index)

    def _on_worker_finished(self) -> None:
        self.progress.setVisible(False)
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        self._worker = None
        self._refresh_toolbar_state()

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Analysis error", message)

    def _stop_worker(self) -> None:
        if self._worker:
            self._worker.request_stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self._worker = None
        self._thread = None
        self.progress.setVisible(False)
        self._refresh_toolbar_state()

    # ------------------------------------------------------------------
    def _update_global_stats(self, stats: dict) -> None:
        self._last_global_stats = stats
        self.global_stats.update_stats(stats)

    def _add_processed_session(self, processed: ProcessedSession) -> None:
        self._processed_sessions.append(processed)
        override = self._session_overrides.get(processed.session.session_id)
        if override:
            processed.payload["override_prompt_path"] = str(override)
        self.session_list.add_session(processed)
        if len(self._processed_sessions) == 1:
            self._on_session_activated(processed)

    def _refresh_session_list(self) -> None:
        selected_id = None
        selected = self.session_list.selected_sessions()
        if selected:
            first = selected[0]
            if isinstance(first, ProcessedSession):
                selected_id = first.session.session_id
        filters = self.session_list.search_box.text()
        method_idx = self.session_list.method_filter.currentIndex()
        ip_idx = self.session_list.ip_filter.currentIndex()
        score_idx = self.session_list.score_filter.currentIndex()

        self.session_list.clear()
        for processed in self._processed_sessions:
            self.session_list.add_session(processed)
        self.session_list.search_box.setText(filters)
        self.session_list.method_filter.setCurrentIndex(min(method_idx, self.session_list.method_filter.count() - 1))
        self.session_list.ip_filter.setCurrentIndex(min(ip_idx, self.session_list.ip_filter.count() - 1))
        self.session_list.score_filter.setCurrentIndex(min(score_idx, self.session_list.score_filter.count() - 1))
        if selected_id:
            for row in range(self.session_list.list_widget.count()):
                entry = self.session_list.list_widget.item(row).data(Qt.UserRole)
                if entry and entry.session_id == selected_id:
                    self.session_list.list_widget.setCurrentRow(row)
                    break

    def _on_session_activated(self, processed: ProcessedSession | dict | None) -> None:
        if not processed:
            self.detail_widget.clear()
            return
        if isinstance(processed, dict):
            for candidate in self._processed_sessions:
                if candidate.payload["session_id"] == processed.get("session_id"):
                    processed = candidate
                    break
        if isinstance(processed, ProcessedSession):
            self.detail_widget.display_session(processed)

    def _on_selection_changed(self, selection: list) -> None:
        if selection:
            processed = selection[0]
            if isinstance(processed, ProcessedSession):
                self._on_session_activated(processed)
        else:
            self.detail_widget.clear()

    def _prompt_rerun(self) -> None:
        if not self._last_log_path:
            QMessageBox.information(self, "Re-run analysis", "Load a log file first.")
            return
        dialog = RerunDialog(
            self,
            model=self._default_model,
            chunk_size=self._default_chunk_size,
            prompt=self._default_prompt_path,
        )
        if dialog.exec() == QDialog.Accepted:
            model, chunk_size, prompt_path = dialog.values()
            if model:
                self._default_model = model
            if chunk_size:
                self._default_chunk_size = chunk_size
            if prompt_path.exists():
                self._default_prompt_path = prompt_path
            self.load_log_file(self._last_log_path)

    def _rerun_session_with_prompt(self, processed: ProcessedSession, prompt_path: Path) -> ProcessedSession:
        session = processed.session
        stats = processed.global_stats
        chunk_size = int(processed.payload.get("chunk_size", self._default_chunk_size))
        chunk_text = build_session_chunk(session, chunk_size)
        try:
            analysis = analyze_logs_ollama_chunk(
                session_id=session.session_id,
                log_chunk=chunk_text,
                prompt_path=str(prompt_path),
                model=self._default_model,
            )
        except Exception as exc:
            analysis = SessionAnalysis(
                session_id=session.session_id,
                anomaly_score=None,
                analyst_note=f"Override failed: {exc}",
                evidence=processed.payload.get("evidence"),
                raw_response=str(exc),
            )
        payload = build_session_payload(session, analysis, stats)
        payload.update(
            {
                "chunk_size": chunk_size,
                "model": self._default_model,
                "prompt_path": str(prompt_path),
                "override_prompt_path": str(prompt_path),
            }
        )
        text_report = format_session_report(session, analysis, stats)
        markdown_report = format_session_markdown(session, analysis, stats)
        return ProcessedSession(
            session=session,
            global_stats=stats,
            payload=payload,
            text_report=text_report,
            markdown_report=markdown_report,
        )

    def _apply_prompt_override(self, path: str) -> None:
        selected = self.session_list.selected_sessions()
        if not selected:
            QMessageBox.information(self, "Prompt override", "Select a session first.")
            return
        override_path = Path(path)
        if not override_path.exists():
            QMessageBox.warning(self, "Prompt override", "Prompt file not found.")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            replacements: list[ProcessedSession] = []
            for item in selected:
                if isinstance(item, ProcessedSession):
                    updated = self._rerun_session_with_prompt(item, override_path)
                    replacements.append(updated)
                    for index, existing in enumerate(self._processed_sessions):
                        if existing.session.session_id == updated.session.session_id:
                            self._processed_sessions[index] = updated
                            break
            if replacements:
                self._session_overrides[replacements[-1].session.session_id] = override_path
                self._refresh_session_list()
                self._on_session_activated(replacements[-1])
        finally:
            QApplication.restoreOverrideCursor()

    # ------------------------------------------------------------------
    def _open_model_manager(self) -> None:
        if self._prompt_manager_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Model manager")
            dialog.resize(420, 560)
            layout = QVBoxLayout(dialog)
            panel = PromptManagerPanel()
            panel.overrideRequested.connect(self._apply_prompt_override)
            layout.addWidget(panel)
            buttons = QDialogButtonBox(QDialogButtonBox.Close)
            buttons.rejected.connect(dialog.reject)
            close_button = buttons.button(QDialogButtonBox.Close)
            if close_button is not None:
                close_button.setText("Close")
            layout.addWidget(buttons)
            self._prompt_manager_dialog = dialog
            self._prompt_manager_panel = panel
        if self._prompt_manager_panel is not None:
            self._prompt_manager_panel.reload()
        self._prompt_manager_dialog.show()
        self._prompt_manager_dialog.raise_()
        self._prompt_manager_dialog.activateWindow()

    # ------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # pragma: no cover - Qt callback
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # pragma: no cover - Qt callback
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.exists():
                self.load_log_file(path)
                break


__all__ = ["KawaiiMainWindow", "ProcessedSession", "AnalysisWorker", "SessionSelectionDialog"]
