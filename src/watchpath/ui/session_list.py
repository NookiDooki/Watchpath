"""Session carousel with advanced filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QSettings,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPen,
)
try:  # PySide6 < 6.5 exposed QShortcut via QtWidgets
    from PySide6.QtGui import QShortcut
except ImportError:  # pragma: no cover - legacy compatibility path
    from PySide6.QtWidgets import QShortcut  # type: ignore[attr-defined]
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QWidget,
)


@dataclass
class SessionListEntry:
    processed: Any
    session_id: str
    ip: str
    methods: Iterable[str]
    score: Optional[float]
    payload: Dict[str, Any]


class SessionListWidget(QWidget):
    """Carousel of sessions supporting multi-select and filters."""

    sessionActivated = Signal(object)
    selectionChanged = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self._entries: List[SessionListEntry] = []
        self._filtered_entries: List[SessionListEntry] = []
        self._pending_method_value: Optional[str] = None
        self._pending_ip_value: Optional[str] = None
        self._restoring_state = False
        self._settings = QSettings("Watchpath", "SessionListWidget")
        self._shortcuts: List[QShortcut] = []

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(6)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Quick search sessions…")
        self.search_box.textChanged.connect(self._apply_filters)
        layout.addWidget(self.search_box, 0, 0, 1, 2)

        self.method_filter = QComboBox()
        self.method_filter.addItem("All methods", None)
        self.method_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.method_filter, 0, 2)

        self.ip_filter = QComboBox()
        self.ip_filter.addItem("All IPs", None)
        self.ip_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.ip_filter, 0, 3)

        self.score_filter = QComboBox()
        self.score_filter.addItems(
            [
                "Any score",
                "High risk (≥ 0.75)",
                "Medium risk (0.4 – 0.74)",
                "Low risk (< 0.4)",
                "No score",
            ]
        )
        self.score_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.score_filter, 0, 4)

        self.clear_filters = QPushButton("Reset filters")
        self.clear_filters.clicked.connect(self._reset_filters)
        layout.addWidget(self.clear_filters, 0, 5)

        self.list_widget = QListView()
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setResizeMode(QListView.Adjust)
        self.list_widget.setMovement(QListView.Static)
        self.list_widget.setSpacing(14)
        self.list_widget.setWrapping(True)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.setSelectionMode(QListView.ExtendedSelection)
        self.list_widget.setWordWrap(True)
        self.list_widget.setObjectName("SessionCarousel")
        self._list_model = _SessionListModel()
        self.list_widget.setModel(self._list_model)
        self._delegate = _SessionItemDelegate(self.list_widget)
        self.list_widget.setItemDelegate(self._delegate)
        self.list_widget.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        self.list_widget.doubleClicked.connect(self._emit_activation)
        layout.addWidget(self.list_widget, 1, 0, 1, 6)

        self.bulk_action_bar = QWidget()
        bulk_layout = QHBoxLayout(self.bulk_action_bar)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.setSpacing(6)
        self.bulk_summary = QLabel()
        self.bulk_summary.setObjectName("BulkSelectionSummary")
        bulk_layout.addWidget(self.bulk_summary)
        bulk_layout.addStretch(1)
        self.bulk_activate = QPushButton("Activate first selection")
        self.bulk_activate.clicked.connect(self._activate_first_selection)
        bulk_layout.addWidget(self.bulk_activate)
        self.bulk_clear = QPushButton("Clear selection")
        self.bulk_clear.clicked.connect(self.list_widget.clearSelection)
        bulk_layout.addWidget(self.bulk_clear)
        self.bulk_action_bar.hide()
        layout.addWidget(self.bulk_action_bar, 2, 0, 1, 6)

        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(4, 1)
        layout.setColumnStretch(5, 0)
        layout.setRowStretch(1, 1)

        self._register_shortcuts()
        self._restore_settings()

    # ------------------------------------------------------------------
    def add_session(self, processed: Any) -> None:
        payload = getattr(processed, "payload", processed)
        session_id = payload.get("session_id", "unknown")
        ip = payload.get("ip", "-")
        methods = payload.get("session_stats", {}).get("method_counts", {}).keys()
        score = payload.get("anomaly_score")
        entry = SessionListEntry(
            processed=processed,
            session_id=session_id,
            ip=ip,
            methods=list(methods),
            score=score,
            payload=payload,
        )
        self._entries.append(entry)
        self._update_filters(entry)
        self._apply_filters()

    def clear(self) -> None:
        self._entries.clear()
        self.method_filter.clear()
        self.method_filter.addItem("All methods", None)
        self.ip_filter.clear()
        self.ip_filter.addItem("All IPs", None)
        self._filtered_entries.clear()
        self._list_model.set_entries([])
        self.list_widget.selectionModel().clearSelection()
        self._save_settings()
        self._update_bulk_actions()

    def selected_payloads(self) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        if not self.list_widget.selectionModel():
            return payloads
        for index in self.list_widget.selectionModel().selectedIndexes():
            entry = index.data(_SessionListModel.EntryRole)
            if isinstance(entry, SessionListEntry):
                payloads.append(entry.payload)
        return payloads

    def selected_sessions(self) -> List[Any]:
        sessions: List[Any] = []
        if not self.list_widget.selectionModel():
            return sessions
        for index in self.list_widget.selectionModel().selectedIndexes():
            entry = index.data(_SessionListModel.EntryRole)
            if isinstance(entry, SessionListEntry):
                sessions.append(entry.processed)
        return sessions

    # ------------------------------------------------------------------
    def _reset_filters(self) -> None:
        self.search_box.clear()
        self.method_filter.setCurrentIndex(0)
        self.ip_filter.setCurrentIndex(0)
        self.score_filter.setCurrentIndex(0)
        self._save_settings()

    def _update_filters(self, entry: SessionListEntry) -> None:
        def _ensure(combo: QComboBox, value: str, label_prefix: str) -> None:
            for index in range(combo.count()):
                if combo.itemData(index) == value:
                    return
            combo.addItem(f"{label_prefix}: {value}", value)

        for method in entry.methods:
            if method:
                _ensure(self.method_filter, method, "Method")
        if entry.ip:
            _ensure(self.ip_filter, entry.ip, "IP")
        self._apply_pending_filter_values()

    def _passes_score_filter(self, score: Optional[float]) -> bool:
        index = self.score_filter.currentIndex()
        if index == 0:
            return True
        if index == 1:
            return isinstance(score, (int, float)) and score >= 0.75
        if index == 2:
            return isinstance(score, (int, float)) and 0.4 <= score < 0.75
        if index == 3:
            return isinstance(score, (int, float)) and score < 0.4
        if index == 4:
            return score is None
        return True

    def _apply_filters(self) -> None:
        query = self.search_box.text().strip().lower()
        method_value = self.method_filter.currentData()
        ip_value = self.ip_filter.currentData()

        self._filtered_entries = []
        for entry in self._entries:
            if query and query not in entry.session_id.lower():
                continue
            if method_value and method_value not in entry.methods:
                continue
            if ip_value and entry.ip != ip_value:
                continue
            if not self._passes_score_filter(entry.score):
                continue
            self._filtered_entries.append(entry)

        if self._filtered_entries:
            self._list_model.set_entries(self._filtered_entries)
            placeholder = False
        else:
            placeholder = True
            message = (
                "No sessions match the current filters."
                if self._entries
                else "No sessions are available yet."
            )
            self._list_model.set_placeholder(message)

        self._restore_default_selection(placeholder)
        self._update_bulk_actions()
        self._save_settings()

    def _restore_default_selection(self, placeholder: bool) -> None:
        if not self.list_widget.selectionModel():
            return
        self.list_widget.selectionModel().clearSelection()
        if not placeholder and self._list_model.rowCount() > 0:
            first = self._list_model.first_selectable_index()
            if first.isValid():
                self.list_widget.setCurrentIndex(first)

    def _on_selection_changed(self, selected, deselected) -> None:
        self._update_bulk_actions()
        sessions = self.selected_sessions()
        self.selectionChanged.emit(sessions)

    def _emit_activation(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        entry = index.data(_SessionListModel.EntryRole)
        if isinstance(entry, SessionListEntry):
            self.sessionActivated.emit(entry.processed)

    def _activate_first_selection(self) -> None:
        sessions = self.selected_sessions()
        if sessions:
            self.sessionActivated.emit(sessions[0])

    def _register_shortcuts(self) -> None:
        shortcuts = [
            ("Ctrl+F", self.search_box.setFocus),
            ("Alt+M", self.method_filter.setFocus),
            ("Alt+I", self.ip_filter.setFocus),
            ("Alt+S", self.score_filter.setFocus),
        ]
        for sequence, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def _restore_settings(self) -> None:
        self._restoring_state = True
        search_value = self._settings.value("filters/search", "", str)
        self.search_box.setText(search_value)
        method_value = self._settings.value("filters/method")
        if method_value:
            self._pending_method_value = str(method_value)
        ip_value = self._settings.value("filters/ip")
        if ip_value:
            self._pending_ip_value = str(ip_value)
        score_index = int(self._settings.value("filters/score_index", 0))
        if 0 <= score_index < self.score_filter.count():
            self.score_filter.setCurrentIndex(score_index)
        self._restoring_state = False
        self._apply_filters()

    def _apply_pending_filter_values(self) -> None:
        if self._pending_method_value is not None:
            index = self._find_combo_index(self.method_filter, self._pending_method_value)
            if index != -1:
                self.method_filter.setCurrentIndex(index)
                self._pending_method_value = None
        if self._pending_ip_value is not None:
            index = self._find_combo_index(self.ip_filter, self._pending_ip_value)
            if index != -1:
                self.ip_filter.setCurrentIndex(index)
                self._pending_ip_value = None

    def _find_combo_index(self, combo: QComboBox, value: str) -> int:
        for idx in range(combo.count()):
            if combo.itemData(idx) == value:
                return idx
        return -1

    def _save_settings(self) -> None:
        if self._restoring_state:
            return
        self._settings.setValue("filters/search", self.search_box.text())
        method_value = self.method_filter.currentData()
        if method_value:
            self._settings.setValue("filters/method", method_value)
        else:
            self._settings.remove("filters/method")
        ip_value = self.ip_filter.currentData()
        if ip_value:
            self._settings.setValue("filters/ip", ip_value)
        else:
            self._settings.remove("filters/ip")
        self._settings.setValue("filters/score_index", self.score_filter.currentIndex())

    def _update_bulk_actions(self) -> None:
        count = len(self.selected_sessions())
        if count:
            self.bulk_summary.setText(f"{count} session(s) selected")
            self.bulk_action_bar.show()
            self.bulk_activate.setEnabled(True)
            self.bulk_clear.setEnabled(True)
        else:
            self.bulk_action_bar.hide()
            self.bulk_summary.clear()
            self.bulk_activate.setEnabled(False)
            self.bulk_clear.setEnabled(False)



class _SessionListModel(QAbstractListModel):
    EntryRole = Qt.UserRole + 1
    PlaceholderRole = Qt.UserRole + 2

    def __init__(self) -> None:
        super().__init__()
        self._entries: List[SessionListEntry] = []
        self._placeholder: Optional[str] = None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        if self._placeholder is not None:
            return 1
        return len(self._entries)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if self._placeholder is not None:
            if role == Qt.DisplayRole:
                return self._placeholder
            if role == self.PlaceholderRole:
                return True
            return None
        entry = self._entries[index.row()]
        if role == Qt.DisplayRole:
            score_text = "Score: N/A"
            if entry.score is not None:
                score_text = f"Score: {entry.score:.2f}"
            methods = ", ".join(entry.methods) if entry.methods else "-"
            return f"{entry.session_id}\n{score_text}\nIP: {entry.ip}\nMethods: {methods}"
        if role == self.EntryRole:
            return entry
        if role == self.PlaceholderRole:
            return False
        if role == Qt.ToolTipRole:
            return f"Session {entry.session_id}\nIP: {entry.ip}"
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        if self._placeholder is not None:
            return Qt.NoItemFlags
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def set_entries(self, entries: List[SessionListEntry]) -> None:
        self.beginResetModel()
        self._placeholder = None
        self._entries = list(entries)
        self.endResetModel()

    def set_placeholder(self, message: str) -> None:
        self.beginResetModel()
        self._entries = []
        self._placeholder = message
        self.endResetModel()

    def first_selectable_index(self) -> QModelIndex:
        if self._placeholder is not None:
            return QModelIndex()
        if not self._entries:
            return QModelIndex()
        return self.index(0, 0)


class _SessionItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = option.rect.adjusted(6, 6, -6, -6)
        placeholder = bool(index.data(_SessionListModel.PlaceholderRole))

        if placeholder:
            self._paint_placeholder(painter, option, rect, index)
        else:
            entry = index.data(_SessionListModel.EntryRole)
            if isinstance(entry, SessionListEntry):
                self._paint_entry(painter, option, rect, entry)
            else:
                self._paint_placeholder(painter, option, rect, index)

        painter.restore()

    def sizeHint(self, option, index: QModelIndex) -> QSize:
        placeholder = bool(index.data(_SessionListModel.PlaceholderRole))
        if placeholder:
            return QSize(260, 100)
        return QSize(260, 140)

    def _paint_placeholder(self, painter: QPainter, option, rect, index: QModelIndex) -> None:
        palette = option.palette
        painter.setPen(Qt.NoPen)
        painter.setBrush(palette.alternateBase())
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(palette.mid().color())
        text = index.data(Qt.DisplayRole) or "No sessions"
        painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, text)

    def _paint_entry(self, painter: QPainter, option, rect, entry: SessionListEntry) -> None:
        palette = option.palette
        base_color = self._score_color(entry.score, palette)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, base_color.lighter(110))
        gradient.setColorAt(1.0, base_color.darker(110))
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 12, 12)

        border_color = (
            palette.highlight().color()
            if option.state & QStyle.State_Selected
            else base_color.darker(150)
        )
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 12, 12)

        painter.setPen(palette.text().color())
        text_rect = rect.adjusted(14, 14, -14, -14)
        font = painter.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignTop | Qt.TextWordWrap, entry.session_id)

        lines = []
        if entry.score is not None:
            lines.append(f"Score: {entry.score:.2f}")
        else:
            lines.append("Score: N/A")
        lines.append(f"IP: {entry.ip}")
        if entry.methods:
            lines.append("Methods: " + ", ".join(entry.methods))

        small_font = QFont(font)
        small_font.setBold(False)
        small_font.setPointSize(max(font.pointSize() - 2, 8))
        painter.setFont(small_font)
        info_rect = text_rect.adjusted(0, 32, 0, 0)
        painter.drawText(info_rect, Qt.AlignTop | Qt.TextWordWrap, "\n".join(lines))

    def _score_color(self, score: Optional[float], palette) -> QColor:
        if score is None:
            return palette.window().color()
        if score >= 0.75:
            return QColor(220, 76, 70)
        if score >= 0.4:
            return QColor(242, 178, 73)
        return QColor(88, 173, 106)
