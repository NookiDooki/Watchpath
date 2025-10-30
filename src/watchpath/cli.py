"""Command line interface for Watchpath."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Sequence

from .ai import analyze_logs_ollama_chunk
from .parser import (
    build_session_chunk,
    build_session_payload,
    format_session_markdown,
    format_session_report,
    load_sessions,
    summarize_sessions,
)

DEFAULT_PROMPT_PATH = Path("prompts/base_prompt.txt")
DEFAULT_SESSION_LIMIT = int(input("How many lines would you like to analyze?: "))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="watchpath",
        description="Analyze web server logs and highlight anomalous sessions.",
    )
    subparsers = parser.add_subparsers(dest="command")

    parse_parser = subparsers.add_parser(
        "parse",
        help="Parse a log file, run anomaly detection, and print a report.",
    )
    parse_parser.add_argument("log_path", help="Path to the log file to analyze.")
    parse_parser.add_argument(
        "--model",
        default="mistral:7b-instruct",
        help="Ollama model name to use for anomaly detection.",
    )
    parse_parser.add_argument(
        "--chunk-size",
        type=int,
        default=50,
        help="Number of log lines to send to the language model per session.",
    )
    parse_parser.add_argument(
        "--prompt",
        default=str(DEFAULT_PROMPT_PATH),
        help="Path to the base prompt template passed to the language model.",
    )
    parse_parser.add_argument(
        "--output-format",
        choices=("text", "markdown", "json"),
        default="text",
        help="Format for the generated report.",
    )
    parse_parser.add_argument(
        "--rich",
        dest="use_rich",
        action="store_true",
        help="Render text output using Rich panels.",
    )
    parse_parser.add_argument(
        "--confirm-each-session",
        action="store_true",
        help="Prompt after each session to decide whether to continue processing.",
    )
    parse_parser.set_defaults(func=_handle_parse_command)

    gui_parser = subparsers.add_parser(
        "gui",
        help="Launch the kawaii Watchpath desktop experience.",
    )
    gui_parser.add_argument(
        "log_path",
        nargs="?",
        help="Optional log file to preload when the GUI opens.",
    )
    gui_parser.add_argument(
        "--model",
        default="mistral:7b-instruct",
        help="Default Ollama model used for anomaly detection.",
    )
    gui_parser.add_argument(
        "--chunk-size",
        type=int,
        default=50,
        help="Number of log lines sent to the model per session.",
    )
    gui_parser.add_argument(
        "--prompt",
        default=str(DEFAULT_PROMPT_PATH),
        help="Prompt template passed to the language model.",
    )
    gui_parser.set_defaults(func=_handle_gui_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


def _handle_parse_command(args: argparse.Namespace) -> int:
    log_path = Path(args.log_path)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    prompt_path = Path(args.prompt)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

    sessions = load_sessions(str(log_path))
    if not sessions:
        print("No sessions found in log.")
        return 0

    sessions = sessions[:DEFAULT_SESSION_LIMIT]

    stats = summarize_sessions(sessions)

    total_sessions = len(sessions)

    rendered_reports: list[str] = []
    json_reports: list[dict] = []
    rich_payloads: list[dict] = []
    stopped_early = False

    for index, session in enumerate(sessions, start=1):
        print(
            f"[{index}/{total_sessions}] Analyzing session {session.session_id}...",
            file=sys.stderr,
            flush=True,
        )
        chunk_text = build_session_chunk(session, args.chunk_size)
        analysis = analyze_logs_ollama_chunk(
            session_id=session.session_id,
            log_chunk=chunk_text,
            prompt_path=str(prompt_path),
            model=args.model,
        )
        payload = build_session_payload(session, analysis, stats)

        if args.output_format == "json":
            json_reports.append(payload)
        elif args.output_format == "markdown":
            rendered_reports.append(format_session_markdown(session, analysis, stats))
        else:
            if getattr(args, "use_rich", False):
                rich_payloads.append(payload)
            else:
                rendered_reports.append(format_session_report(session, analysis, stats))

        if getattr(args, "confirm_each_session", False):
            if not _prompt_to_continue():
                stopped_early = True
                break

    if sessions:
        message = "Analysis complete."
        if stopped_early:
            message = "Analysis stopped early at user request."
        print(message, file=sys.stderr, flush=True)

    if args.output_format == "json":
        print(json.dumps(json_reports, indent=2))
    elif args.output_format == "markdown":
        print("\n\n".join(rendered_reports))
    elif getattr(args, "use_rich", False):
        _print_rich_reports(rich_payloads)
    else:
        print("\n\n".join(rendered_reports))
    return 0


def _handle_gui_command(args: argparse.Namespace) -> int:
    from .gui import launch_gui

    prompt_path = Path(args.prompt)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

    return launch_gui(
        args.log_path,
        model=args.model,
        chunk_size=args.chunk_size,
        prompt_path=str(prompt_path),
    )


def _prompt_to_continue() -> bool:
    """Prompt the user to continue processing additional sessions."""

    sys.stderr.write("Continue to next session? [Y/n]: ")
    sys.stderr.flush()

    try:
        response = input().strip().lower()
    except EOFError:
        return False

    if not response:
        return True

    return response in {"y", "yes"}


def _print_rich_reports(payloads: list[dict]) -> None:
    """Render session reports as Rich panels."""

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    for payload in payloads:
        session_stats = payload["session_stats"]
        global_stats = payload["global_stats"]

        table = Table.grid(expand=True)
        table.add_column(justify="left")
        score = payload["anomaly_score"] if payload["anomaly_score"] is not None else "N/A"
        table.add_row(f"⚠️ [bold]Anomaly Score[/]: {score}")
        table.add_row(f"🧠 [bold]Analyst Note[/]: {payload['analyst_note']}")
        table.add_row("📊 [bold]Session Statistics[/]:")
        table.add_row(
            "  • Duration: {duration:.0f}s | Requests: {requests} | Unique Paths: {paths}".format(
                duration=session_stats["duration_seconds"],
                requests=session_stats["request_count"],
                paths=session_stats["unique_path_count"],
            )
        )
        method_summary = ", ".join(
            f"{method} ({count})" for method, count in Counter(session_stats["method_counts"]).most_common()
        ) or "None"
        table.add_row(f"  • Methods: {method_summary}")
        table.add_row("📊 [bold]Global Statistics[/]:")
        ip_summary = ", ".join(f"{ip}: {count}" for ip, count in global_stats["top_ips"]) or "None"
        table.add_row(
            "  • Mean Duration: {duration:.0f}s | Top IPs: {ips}".format(
                duration=global_stats["mean_session_duration_seconds"],
                ips=ip_summary,
            )
        )

        panel = Panel(
            table,
            title=f"Session {payload['session_id']} ({payload['ip']} / {payload['user']})",
            expand=True,
        )
        console.print(panel)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
