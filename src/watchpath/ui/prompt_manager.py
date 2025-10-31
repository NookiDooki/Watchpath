"""Prompt manager panel for managing analysis templates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)



# ╭──────────────────────────────────────────────────────────────╮
# │ Metadata carrier for prompt templates.                       │
# ╰──────────────────────────────────────────────────────────────╯


@dataclass
class PromptEntry:
    path: Path
    title: str
    folder_display: str
    folder_terms: str
    modified: datetime


class PromptManagerPanel(QWidget):
    """Browse prompt templates, preview contents, and manage overrides."""

    # ╭──────────────────────────────────────────────────────────╮
    # │ Signals                                                   │
    # ╰──────────────────────────────────────────────────────────╯

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

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter prompts…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_input)

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

        self._prompt_entries: list[PromptEntry] = []
        self.reload()

    # ------------------------------------------------------------------
    def set_prompt_root(self, root: Path) -> None:
        self._prompt_root = root
        self.reload()

    def reload(self) -> None:
        self._prompt_entries = []
        self.prompt_list.clear()
        if not self._prompt_root.exists():
            return
        for path in sorted(self._prompt_root.glob("**/*.txt")):
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            relative_folder = path.parent.relative_to(self._prompt_root)
            folder_terms = "" if relative_folder == Path(".") else relative_folder.as_posix()
            folder_display = folder_terms if folder_terms else "(root)"
            entry = PromptEntry(
                path=path,
                title=path.stem,
                folder_display=folder_display,
                folder_terms=folder_terms,
                modified=modified,
            )
            self._prompt_entries.append(entry)
        self._populate_prompt_list(self.search_input.text())

    def _on_prompt_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        if not current:
            self.preview.clear()
            self.history_list.clear()
            return
        path: Path = current.data(Qt.UserRole)
        self.preview.setPlainText(path.read_text(encoding="utf-8"))
        self._populate_history(path)

    # ╭──────────────────────────────────────────────────────────╮
    # │ Filtering + selection logic                               │
    # ╰──────────────────────────────────────────────────────────╯
    def _populate_prompt_list(self, filter_text: str = "") -> None:
        current_path: Optional[Path] = None
        current_item = self.prompt_list.currentItem()
        if current_item:
            current_path = current_item.data(Qt.UserRole)

        self.prompt_list.blockSignals(True)
        self.prompt_list.clear()

        normalized = filter_text.strip().lower()
        to_select: Optional[QListWidgetItem] = None

        for entry in self._prompt_entries:
            haystack = f"{entry.title} {entry.folder_display} {entry.folder_terms}".lower()
            if normalized and normalized not in haystack:
                continue
            item = QListWidgetItem()
            item.setData(Qt.UserRole, entry.path)
            widget = PromptListItemWidget(entry)
            item.setSizeHint(widget.sizeHint())
            self.prompt_list.addItem(item)
            self.prompt_list.setItemWidget(item, widget)
            if current_path and entry.path == current_path:
                to_select = item

        self.prompt_list.blockSignals(False)

        if to_select is not None:
            self.prompt_list.setCurrentItem(to_select)
        elif self.prompt_list.count():
            self.prompt_list.setCurrentRow(0)
        else:
            self.preview.clear()
            self.history_list.clear()

    def _apply_filter(self, text: str) -> None:
        self._populate_prompt_list(text)

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
            # Emit the Qt signal as a plain string to keep slots flexible.
            self.overrideRequested.emit(str(path))

    def apply_override(self, path: str) -> None:
        """Update the preview to show the override path."""

        target = Path(path)
        if target.exists():
            self.preview.setPlainText(target.read_text(encoding="utf-8"))


class PromptListItemWidget(QWidget):
    """Rich display for prompt entries in the list widget."""

    # A dash of neon highlights prompt titles without custom delegates.

    def __init__(self, entry: PromptEntry) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        title_label = QLabel(entry.title)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        meta_label = QLabel(
            f"{entry.folder_display} • Updated {entry.modified:%Y-%m-%d %H:%M}"
        )
        meta_font = meta_label.font()
        meta_font.setPointSize(max(meta_font.pointSize() - 1, 8))
        meta_label.setFont(meta_font)
        meta_label.setStyleSheet("color: palette(mid);")
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)

        layout.addStretch(1)
