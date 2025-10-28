"""Kawaii desktop interface for Watchpath log analysis."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from .app import KawaiiMainWindow


def launch_gui(
    log_path: str | None = None,
    *,
    model: str = "mistral:7b-instruct",
    chunk_size: int = 50,
    prompt_path: str | None = None,
) -> int:
    """Launch the Watchpath kawaii GUI.

    Parameters
    ----------
    log_path:
        Optional log file to automatically load once the application starts.
    model:
        Default Ollama model to use for anomaly analysis.
    chunk_size:
        Number of log lines to feed into the model for each session.
    prompt_path:
        Optional override for the base prompt template.
    """

    import sys

    from PySide6.QtWidgets import QApplication

    from .app import KawaiiMainWindow  # Imported lazily to avoid mandatory PySide6 dependency

    app = QApplication.instance() or QApplication(sys.argv)

    window = KawaiiMainWindow(
        default_model=model,
        default_chunk_size=chunk_size,
        default_prompt_path=Path(prompt_path) if prompt_path else None,
    )
    window.show()

    if log_path:
        # Defer loading until the event loop is running so progress widgets update.
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: window.load_log_file(Path(log_path)))

    return app.exec()


def __getattr__(name: str):  # pragma: no cover - simple module re-export helper
    if name == "KawaiiMainWindow":
        from .app import KawaiiMainWindow as _KawaiiMainWindow

        return _KawaiiMainWindow
    raise AttributeError(name)


__all__ = ["launch_gui", "KawaiiMainWindow"]
