"""Conversion utilities for transforming Watchpath JSON output into Markdown."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence


def _format_list(items: Sequence[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _render_chart_block(chart: Dict[str, Any], chart_rel_dir: Path) -> str:
    status = chart.get("status")
    filename = chart.get("filename")
    alt_text = chart.get("alt_text", "Chart")
    caption = chart.get("caption", "")
    explanation = chart.get("explanation")

    if status != "present" or not filename:
        parts = [f"> Chart unavailable: {alt_text}."]
        if caption:
            parts.append(f"> Expected insight: {caption}")
        if explanation:
            parts.append(f"> {explanation}")
        return "\n".join(parts)

    rel_path = chart_rel_dir / filename
    block_lines = [
        f"![{alt_text}]({rel_path.as_posix()})",
    ]
    if caption:
        block_lines.append(f"<small>{caption}</small>")
    if explanation:
        block_lines.append(f"_{explanation}_")
    return "\n".join(block_lines)


def render_markdown_from_json(
    payload: Dict[str, Any],
    chart_rel_dir: Path,
    section_title: str,
) -> str:
    lines: List[str] = [f"## {section_title}"]

    executive_summary = payload.get("executive_summary", [])
    if executive_summary:
        lines.append("### Executive Summary")
        for item in executive_summary:
            insight = item.get("insight", "Insight not provided")
            impact = item.get("impact", "Impact not specified")
            lines.append(f"- **{insight}** — {impact}")
            for chart in item.get("supporting_charts", []):
                lines.append(_render_chart_block(chart, chart_rel_dir))
    else:
        lines.append("No executive summary provided.")

    key_findings = payload.get("key_findings", [])
    if key_findings:
        lines.append("\n### Key Findings")
        for finding in key_findings:
            title = finding.get("title", "Untitled Finding")
            details = finding.get("details", "No details supplied.")
            lines.append(f"#### {title}")
            lines.append(details)

            evidence_items = finding.get("evidence", [])
            if evidence_items:
                lines.append("Evidence:")
                for chart in evidence_items:
                    lines.append(_render_chart_block(chart, chart_rel_dir))
            related_entities = finding.get("related_entities", [])
            if related_entities:
                lines.append("Related Entities:")
                for entity in related_entities:
                    lines.append(
                        f"- {entity.get('type', 'entity')}: {entity.get('value', 'unknown')} — {entity.get('role', 'role unspecified')}"
                    )
    else:
        lines.append("\n### Key Findings\nNo key findings provided.")

    confidence = payload.get("confidence_and_assumptions", {})
    if confidence:
        lines.append("\n### Confidence & Assumptions")
        confidence_level = confidence.get("confidence_level", "Unknown")
        lines.append(f"- **Confidence Level:** {confidence_level}")
        lines.append("- **Assumptions:**")
        lines.append(_format_list(confidence.get("assumptions", [])))
        lines.append("- **Data Gaps:**")
        lines.append(_format_list(confidence.get("data_gaps", [])))
        lines.append("- **Recommended Follow-up:**")
        lines.append(_format_list(confidence.get("recommended_follow_up", [])))

    high_risk = payload.get("high_risk_actors", [])
    lines.append("\n### High-Risk Actors")
    if high_risk:
        lines.append("| Type | Value | Reason | Confidence |")
        lines.append("| --- | --- | --- | --- |")
        for actor in high_risk:
            lines.append(
                "| {type} | {value} | {reason} | {confidence} |".format(
                    type=actor.get("type", "unknown"),
                    value=actor.get("value", "n/a"),
                    reason=actor.get("reason", "no reason supplied"),
                    confidence=actor.get("confidence", "Unknown"),
                )
            )
    else:
        lines.append("- None identified")

    next_steps = payload.get("next_steps", [])
    lines.append("\n### Next Steps")
    if next_steps:
        for step in next_steps:
            action = step.get("action", "Action not provided")
            linked = step.get("linked_finding", "No linked finding")
            priority = step.get("priority", "Unspecified")
            owner = step.get("owner", "Unassigned")
            lines.append(
                f"- [ ] ({priority}) {action} — Owner: {owner} (Linked finding: {linked})"
            )
    else:
        lines.append("- [ ] (Low) No follow-up steps provided")

    return "\n".join(lines)


def parse_json_payload(raw_output: str) -> Dict[str, Any]:
    """Parse the JSON response from the LLM, raising a ValueError on failure."""
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON payload: {exc}") from exc
