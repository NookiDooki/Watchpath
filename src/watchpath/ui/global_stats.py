"""Global statistics dashboard widgets."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Tuple

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, QPointF, Qt, Signal
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QToolButton,
    QToolTip,
    QVBoxLayout,
)


class GlobalStatsWidget(QFrame):
    """Display global statistics with interactive charts."""

    dataPointActivated = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("GlobalStats")
        self._stats: Dict[str, object] = {}
        self._timeline_lookup: Dict[int, Tuple[str, int]] = {}
        self._timeline_series: QLineSeries | None = None
        self._active_mode = "Overview"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.title = QLabel("🌐 Global insights")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title.setFont(title_font)
        header_layout.addWidget(self.title)

        header_layout.addStretch(1)

        self.mode_buttons: Dict[str, QToolButton] = {}
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(4)
        for mode in ("Overview", "Status codes", "Traffic timeline"):
            button = QToolButton()
            button.setText(mode)
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.clicked.connect(lambda checked, m=mode: self._set_mode(m))
            self.mode_group.addButton(button)
            self.mode_buttons[mode] = button
            chips_layout.addWidget(button)
        header_layout.addLayout(chips_layout)

        layout.addLayout(header_layout)

        metrics_frame = QFrame()
        metrics_layout = QHBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(12)
        self.metric_tiles = {}
        for key, title in (
            ("requests", "Total requests"),
            ("duration", "Avg. session"),
            ("ips", "Active IPs"),
        ):
            tile, value_label = self._build_metric_tile(title, "--")
            self.metric_tiles[key] = value_label
            metrics_layout.addWidget(tile)
        layout.addWidget(metrics_frame)

        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing, True)
        self.chart_view.setMouseTracking(True)

        self.chart_placeholder = QLabel("Loading analytics…")
        self.chart_placeholder.setAlignment(Qt.AlignCenter)
        self.chart_placeholder.setWordWrap(True)

        self.chart_frame = QFrame()
        self.chart_stack = QStackedLayout(self.chart_frame)
        self.chart_stack.addWidget(self.chart_placeholder)
        self.chart_stack.addWidget(self.chart_view)

        layout.addWidget(self.chart_frame, 1)

        self.footer = QLabel("Hover a data point to explore details.")
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)

        # Initialize with the default mode selected.
        self._set_mode(self._active_mode)

    # ------------------------------------------------------------------
    def update_stats(self, stats: Dict[str, object]) -> None:
        """Refresh the charts with ``stats``."""

        self._stats = stats or {}
        self._refresh_metrics()
        self._render_summary()

    # ------------------------------------------------------------------
    def _set_mode(self, mode: str) -> None:
        if (
            mode == self._active_mode
            and self.mode_buttons.get(mode, None)
            and self.mode_buttons[mode].isChecked()
        ):
            self.footer.setText(f"{mode} insights ready.")
            self._render_summary()
            return

        self._active_mode = mode
        button = self.mode_buttons.get(mode)
        if button and not button.isChecked():
            button.setChecked(True)
        self.footer.setText(f"{mode} insights ready.")
        self._render_summary()

    # ------------------------------------------------------------------
    def _render_summary(self) -> None:
        mode = self._active_mode
        if not self._stats:
            self._show_placeholder("Loading analytics… Hang tight while we crunch the numbers.")
            self.footer.setText(f"{mode} metrics are loading…")
            return

        error_message = self._stats.get("error") if isinstance(self._stats, dict) else None
        if error_message:
            self._show_placeholder(f"⚠️ Unable to load analytics. {error_message}")
            self.footer.setText("Retry after resolving the data source issue.")
            return

        if mode == "Status codes":
            self._render_status_distribution()
        elif mode == "Traffic timeline":
            self._render_timeline()
        else:
            self._render_overview()

    def _render_overview(self) -> None:
        chart = QChart()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(False)

        request_counts: Dict[str, int] = dict(
            self._stats.get("request_counts", {}) or {}
        )
        series = QBarSeries()
        total_requests = 0
        if request_counts:
            # Sort alphabetically for stability.
            categories = sorted(request_counts)
            values = [request_counts[method] for method in categories]
            bar_set = QBarSet("Requests")
            bar_set.append(values)
            bar_set.clicked.connect(self._emit_method_activation)  # type: ignore[attr-defined]
            series.append(bar_set)
            chart.addSeries(series)

            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)

            axis_y = QValueAxis()
            axis_y.setTitleText("Requests")
            axis_y.applyNiceNumbers()
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
            total_requests = sum(values)
        else:
            self._show_placeholder("No request data available yet")

        mean_duration = self._stats.get("mean_session_duration_seconds") or 0.0
        top_ips = self._stats.get("top_ips") or []
        top_summary = ", ".join(f"{ip} ({count})" for ip, count in top_ips) or "No IP data"
        self.footer.setText(
            f"Average session duration: {self._format_duration(mean_duration)} • "
            f"Total requests: {total_requests} • Frequent IPs: {top_summary}"
        )

        if request_counts:
            self._display_chart(chart)

    def _render_status_distribution(self) -> None:
        chart = QChart()
        chart.setTitle("Status code distribution")
        chart.legend().setVisible(False)
        chart.setAnimationOptions(QChart.SeriesAnimations)

        status_distribution: Dict[int, int] = dict(
            self._stats.get("status_distribution", {}) or {}
        )
        series = QBarSeries()
        if status_distribution:
            ordered_codes = sorted(status_distribution)
            categories = [str(code) for code in ordered_codes]
            values = [status_distribution[code] for code in ordered_codes]
            bar_set = QBarSet("Responses")
            bar_set.append(values)
            series.append(bar_set)
            chart.addSeries(series)

            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)

            axis_y = QValueAxis()
            axis_y.setTitleText("Responses")
            axis_y.applyNiceNumbers()
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
            self.footer.setText(
                "Status mix: "
                + ", ".join(f"{code}: {count}" for code, count in sorted(status_distribution.items()))
            )
        else:
            chart.setTitle("No status codes observed yet")
            self.footer.setText("Status code data will appear after analysing sessions.")

        if not status_distribution:
            self._show_placeholder("No status codes observed yet")
        else:
            bar_set.clicked.connect(self._emit_status_activation)  # type: ignore[attr-defined]
            self._display_chart(chart)

    def _render_timeline(self) -> None:
        chart = QChart()
        chart.setTitle("Request timeline")
        chart.legend().setVisible(False)
        chart.setAnimationOptions(QChart.SeriesAnimations)

        series = QLineSeries()
        timeline: Iterable[Tuple[str, int]] = self._stats.get("request_timeline", []) or []
        self._timeline_lookup.clear()
        timestamps: list[QDateTime] = []
        for timestamp, count in timeline:
            dt = self._parse_timestamp(timestamp)
            if dt is None:
                continue
            msecs = dt.toMSecsSinceEpoch()
            series.append(float(msecs), float(count))
            self._timeline_lookup[int(msecs)] = (timestamp, count)
            timestamps.append(dt)
        chart.addSeries(series)

        axis_x = QDateTimeAxis()
        axis_x.setTitleText("Timeline")
        axis_x.setFormat("yyyy-MM-dd HH:mm")
        if timestamps:
            axis_x.setRange(timestamps[0], timestamps[-1])
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Requests per bucket")
        axis_y.applyNiceNumbers()
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        if timeline and timestamps:
            start, end = timeline[0][0], timeline[-1][0]
            self.footer.setText(
                f"Activity spans from {start} to {end}. Hover to inspect density."
            )
            self._timeline_series = series
            series.hovered.connect(self._show_timeline_tooltip)
            series.pointClicked.connect(self._emit_timeline_activation)
            self._display_chart(chart)
        elif timeline and not timestamps:
            self.footer.setText("Timeline data is available but could not be parsed.")
            self._show_placeholder("Timeline data could not be parsed.")
            self._timeline_series = None
        else:
            self.footer.setText("Timeline will populate once traffic is analysed.")
            self._show_placeholder("Timeline will populate once traffic is analysed.")
            self._timeline_series = None

    # ------------------------------------------------------------------
    def _build_metric_tile(self, title: str, value: str) -> Tuple[QFrame, QLabel]:
        tile = QFrame()
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(12, 12, 12, 12)
        tile_layout.setSpacing(4)

        caption = QLabel(title)
        caption_font = QFont()
        caption_font.setPointSize(10)
        caption.setFont(caption_font)
        caption.setProperty("class", "MetricTileCaption")

        metric_value = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(18)
        value_font.setBold(True)
        metric_value.setFont(value_font)
        metric_value.setProperty("class", "MetricTileValue")

        tile_layout.addWidget(caption)
        tile_layout.addWidget(metric_value)

        return tile, metric_value

    def _refresh_metrics(self) -> None:
        total_requests = 0
        request_counts: Dict[str, int] = dict(self._stats.get("request_counts", {}) or {})
        if request_counts:
            total_requests = sum(request_counts.values())

        mean_duration = self._stats.get("mean_session_duration_seconds") or 0.0
        top_ips = self._stats.get("top_ips") or []

        self._set_tile_value("requests", f"{total_requests:,}" if total_requests else "--")
        self._set_tile_value("duration", self._format_duration(mean_duration))
        self._set_tile_value("ips", str(len(top_ips)) if top_ips else "--")

    def _set_tile_value(self, key: str, value: str) -> None:
        label = self.metric_tiles.get(key)
        if label:
            label.setText(value)

    def _display_chart(self, chart: QChart) -> None:
        self.chart_view.setChart(chart)
        self.chart_stack.setCurrentWidget(self.chart_view)

    def _show_placeholder(self, message: str) -> None:
        self.chart_placeholder.setText(message)
        self.chart_stack.setCurrentWidget(self.chart_placeholder)

    def _parse_timestamp(self, timestamp: str) -> QDateTime | None:
        try:
            cleaned = timestamp.replace("Z", "+00:00") if timestamp.endswith("Z") else timestamp
            dt_obj = datetime.fromisoformat(cleaned)
        except ValueError:
            return None
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return QDateTime(dt_obj)

    def _show_timeline_tooltip(self, point: QPointF, state: bool) -> None:
        if not state:
            QToolTip.hideText()
            return

        lookup_key = int(round(point.x()))
        bucket = self._timeline_lookup.get(lookup_key)
        if not bucket:
            return

        timestamp, count = bucket
        chart = self.chart_view.chart()
        series = getattr(self, "_timeline_series", None)
        position = chart.mapToPosition(point, series) if series is not None else chart.mapToPosition(point)
        global_pos = self.chart_view.mapToGlobal(position.toPoint())
        QToolTip.showText(global_pos, f"{timestamp}\nRequests: {count}", self.chart_view)

    def _emit_timeline_activation(self, point: QPointF) -> None:
        lookup_key = int(round(point.x()))
        bucket = self._timeline_lookup.get(lookup_key)
        if bucket:
            timestamp, _ = bucket
            self.dataPointActivated.emit(timestamp)

    def _emit_status_activation(self, index: int) -> None:
        status_distribution: Dict[int, int] = dict(
            self._stats.get("status_distribution", {}) or {}
        )
        ordered_codes = sorted(status_distribution)
        if 0 <= index < len(ordered_codes):
            self.dataPointActivated.emit(str(ordered_codes[index]))

    def _emit_method_activation(self, index: int) -> None:
        request_counts: Dict[str, int] = dict(
            self._stats.get("request_counts", {}) or {}
        )
        categories = sorted(request_counts)
        if 0 <= index < len(categories):
            self.dataPointActivated.emit(categories[index])

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {sec}s"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"
