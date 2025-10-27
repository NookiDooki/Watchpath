"""Compatibility shim that forwards to :mod:`watchpath.cli`."""

from __future__ import annotations

from watchpath.cli import main


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
