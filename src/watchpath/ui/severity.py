"""Shared helpers for mapping anomaly scores to expressive UI styles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SeverityStyle:
    """Presentation attributes for a given anomaly severity."""

    label: str
    kaomoji: str
    color: str
    emoji: str


_UNKNOWN_STYLE = SeverityStyle(
    label="Unknown",
    kaomoji="(=^‥^=)",
    color="#65c466",
    emoji="❔",
)

_ZERO_STYLE = SeverityStyle(
    label="Serene",
    kaomoji="o(=´∇｀=)o",
    color="#2ecc71",
    emoji="🌿",
)

_LOW_STYLE = SeverityStyle(
    label="Playful",
    kaomoji="(=^･ω･^=)ﾉ♡",
    color="#5dd39e",
    emoji="😺",
)

_MODERATE_STYLE = SeverityStyle(
    label="Alert",
    kaomoji="(=｀ω´=)ゞ",
    color="#f6c343",
    emoji="👀",
)

_HIGH_STYLE = SeverityStyle(
    label="Tense",
    kaomoji="(=｀^´=)!!",
    color="#fb8c00",
    emoji="⚠️",
)

_CRITICAL_STYLE = SeverityStyle(
    label="Alarmed",
    kaomoji="(=；｀ω´=)!!!",
    color="#ef5350",
    emoji="🚨",
)

_TOTAL_STYLE = SeverityStyle(
    label="Catastrophic",
    kaomoji="٩(=◎皿◎=)۶",
    color="#c62828",
    emoji="💥",
)


def severity_for_score(score: Optional[float]) -> SeverityStyle:
    """Return the presentation style that matches the anomaly score."""

    if not isinstance(score, (int, float)):
        return _UNKNOWN_STYLE

    percent = max(0.0, min(float(score) * 100.0, 100.0))
    if percent == 0.0:
        return _ZERO_STYLE
    if percent <= 25.0:
        return _LOW_STYLE
    if percent <= 50.0:
        return _MODERATE_STYLE
    if percent <= 75.0:
        return _HIGH_STYLE
    if percent < 100.0:
        return _CRITICAL_STYLE
    return _TOTAL_STYLE


def severity_label(score: Optional[float]) -> str:
    """Return a human readable label for the anomaly score."""

    return severity_for_score(score).label
