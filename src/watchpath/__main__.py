"""Module entry point for ``python -m watchpath``."""

from __future__ import annotations

from .cli import main


def run() -> int:
    # Keep this minimal so ``python -m watchpath`` stays lightning fast.
    return main()


if __name__ == "__main__":  # pragma: no cover - standard entry point
    raise SystemExit(run())
