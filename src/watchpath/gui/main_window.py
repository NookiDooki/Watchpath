"""Main window implementation for the Watchpath GUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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

            self.status.emit("🌸 Preparing tea and parsing sessions…")
            sessions = load_sessions(str(self.log_path))
            if not sessions:
                raise RuntimeError("No sessions discovered in the selected log file.")

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
        self.addToolBar(toolbar)

        open_action = QAction("Open log 🍡", self)
        open_action.triggered.connect(self._choose_log_file)
        toolbar.addAction(open_action)

        rerun_action = QAction("Re-run with alternate parameters", self)
        rerun_action.triggered.connect(self._prompt_rerun)
        toolbar.addAction(rerun_action)

        stop_action = QAction("Stop analysis", self)
        stop_action.triggered.connect(self._stop_worker)
        toolbar.addAction(stop_action)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        toolbar.addWidget(self.theme_combo)

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

        self.setCentralWidget(central)
        self._apply_theme()

    # ------------------------------------------------------------------
    def _apply_theme(self) -> None:
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else "dark"
        app = QApplication.instance()
        if not app:
            return
        if theme == "light":
            app.setStyleSheet(
                "QMainWindow { background: #fdf9ff; color: #2d334a; }"
                "QLabel { color: #2d334a; }"
            )
        else:
            app.setStyleSheet(
                "QMainWindow { background: #101421; color: #edf1ff; }"
                "QLabel { color: #edf1ff; }"
            )

    # ------------------------------------------------------------------
    def _choose_log_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select access log",
            "",
            "Log files (*.log *.txt);;All files (*)",
        )
        if path:
            self.load_log_file(Path(path))

    def load_log_file(self, path: Path) -> None:
        self._last_log_path = path
        self.session_list.clear()
        self.detail_widget.clear()
        self._processed_sessions.clear()
        self._session_overrides.clear()
        self._start_worker(
            log_path=path,
            model=self._default_model,
            chunk_size=self._default_chunk_size,
            prompt_path=self._default_prompt_path,
        )

    def _start_worker(self, *, log_path: Path, model: str, chunk_size: int, prompt_path: Path) -> None:
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


__all__ = ["KawaiiMainWindow", "ProcessedSession", "AnalysisWorker"]
