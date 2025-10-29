"""Prompt manager panel for managing analysis templates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PromptManagerPanel(QWidget):
    """Browse prompt templates, preview contents, and manage overrides."""

    overrideRequested = Signal(str)

    def __init__(self, prompt_root: Optional[Path] = None) -> None:
        super().__init__()
        self._prompt_root = prompt_root or Path("prompts")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Prompt manager")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.prompt_list = QListWidget()
        self.prompt_list.currentItemChanged.connect(self._on_prompt_selected)
        layout.addWidget(self.prompt_list, 1)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select a template to preview its contents…")
        layout.addWidget(self.preview, 2)

        history_label = QLabel("Version history")
        layout.addWidget(history_label)
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._on_history_activated)
        layout.addWidget(self.history_list, 1)

        controls = QHBoxLayout()
        self.override_button = QPushButton("Use for session")
        self.override_button.clicked.connect(self._request_override)
        controls.addWidget(self.override_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.reload)
        controls.addWidget(refresh_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.reload()

    # ------------------------------------------------------------------
    def set_prompt_root(self, root: Path) -> None:
        self._prompt_root = root
        self.reload()

    def reload(self) -> None:
        self.prompt_list.clear()
        if not self._prompt_root.exists():
            return
        for path in sorted(self._prompt_root.glob("**/*.txt")):
            item = QListWidgetItem(path.stem)
            item.setData(Qt.UserRole, path)
            self.prompt_list.addItem(item)
        if self.prompt_list.count():
            self.prompt_list.setCurrentRow(0)

    def _on_prompt_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        if not current:
            self.preview.clear()
            self.history_list.clear()
            return
        path: Path = current.data(Qt.UserRole)
        self.preview.setPlainText(path.read_text(encoding="utf-8"))
        self._populate_history(path)

    def _populate_history(self, path: Path) -> None:
        history_root = path.parent / ".history"
        self.history_list.clear()
        if history_root.exists():
            entries = sorted(history_root.glob(f"{path.stem}_*.txt"), reverse=True)
            for entry in entries:
                item = QListWidgetItem(entry.stem)
                item.setData(Qt.UserRole, entry)
                self.history_list.addItem(item)
        else:
            timestamp = datetime.fromtimestamp(path.stat().st_mtime)
            item = QListWidgetItem(f"Last updated: {timestamp:%Y-%m-%d %H:%M:%S}")
            self.history_list.addItem(item)

    def _on_history_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if isinstance(path, Path) and path.exists():
            self.preview.setPlainText(path.read_text(encoding="utf-8"))

    def _request_override(self) -> None:
        current = self.prompt_list.currentItem()
        if not current:
            return
        path: Path = current.data(Qt.UserRole)
        if path:
            self.overrideRequested.emit(str(path))

    def apply_override(self, path: str) -> None:
        """Update the preview to show the override path."""

        target = Path(path)
        if target.exists():
            self.preview.setPlainText(target.read_text(encoding="utf-8"))
