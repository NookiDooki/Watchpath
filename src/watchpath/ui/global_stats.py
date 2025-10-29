"""Global statistics dashboard widgets."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout


class GlobalStatsWidget(QFrame):
    """Display global statistics with interactive charts."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("GlobalStats")
        self._stats: Dict[str, object] = {}

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

        self.summary_toggle = QComboBox()
        self.summary_toggle.addItems([
            "Overview",
            "Status codes",
            "Traffic timeline",
        ])
        self.summary_toggle.currentIndexChanged.connect(self._render_summary)
        header_layout.addWidget(self.summary_toggle)

        layout.addLayout(header_layout)

        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing, True)
        layout.addWidget(self.chart_view, 1)

        self.footer = QLabel("Hover a data point to explore details.")
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)

        self._render_summary()

    # ------------------------------------------------------------------
    def update_stats(self, stats: Dict[str, object]) -> None:
        """Refresh the charts with ``stats``."""

        self._stats = stats or {}
        self._render_summary()

    # ------------------------------------------------------------------
    def _render_summary(self) -> None:
        mode = self.summary_toggle.currentText()
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
        if request_counts:
            # Sort alphabetically for stability.
            categories = sorted(request_counts)
            values = [request_counts[method] for method in categories]
            bar_set = QBarSet("Requests")
            bar_set.append(values)
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
            total_requests = 0

        mean_duration = self._stats.get("mean_session_duration_seconds") or 0.0
        top_ips = self._stats.get("top_ips") or []
        top_summary = ", ".join(f"{ip} ({count})" for ip, count in top_ips) or "No IP data"
        self.footer.setText(
            f"Average session duration: {self._format_duration(mean_duration)} • "
            f"Total requests: {total_requests} • Frequent IPs: {top_summary}"
        )

        if not request_counts:
            chart.setTitle("No request data available yet")

        self.chart_view.setChart(chart)

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

        self.chart_view.setChart(chart)

    def _render_timeline(self) -> None:
        chart = QChart()
        chart.setTitle("Request timeline")
        chart.legend().setVisible(False)
        chart.setAnimationOptions(QChart.SeriesAnimations)

        series = QLineSeries()
        timeline: Iterable[Tuple[str, int]] = self._stats.get("request_timeline", []) or []
        for index, (timestamp, count) in enumerate(timeline):
            series.append(float(index), float(count))
        chart.addSeries(series)

        axis_x = QValueAxis()
        axis_x.setLabelFormat("%d")
        axis_x.setTitleText("Time buckets")
        upper = max(series.count() - 1, 0)
        axis_x.setRange(0, max(upper, 0))
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Requests per bucket")
        axis_y.applyNiceNumbers()
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        if timeline:
            start, end = timeline[0][0], timeline[-1][0]
            self.footer.setText(
                f"Activity spans from {start} to {end}. Hover to inspect density."
            )
        else:
            self.footer.setText("Timeline will populate once traffic is analysed.")

        self.chart_view.setChart(chart)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {sec}s"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"
