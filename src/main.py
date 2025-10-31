"""Compatibility shim that forwards to :mod:`watchpath.cli`."""

from __future__ import annotations

from watchpath.cli import main

# ╭──────────────────────────────────────────────────────────────╮
# │ Allow ``python src/main.py`` for legacy entry points.        │
# ╰──────────────────────────────────────────────────────────────╯


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
