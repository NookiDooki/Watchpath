"""Core log analysis helpers that interface with Ollama."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import subprocess
from typing import Iterator

__all__ = [
    "OllamaAnalyzer",
    "OllamaConfig",
    "OllamaError",
    "analyze_log_file",
    "analyze_logs_ollama_chunk",
    "chunk_log_file",
    "load_prompt",
]


class OllamaError(RuntimeError):
    """Raised when Ollama fails to process a request."""


@dataclass(frozen=True)
class OllamaConfig:
    """Configuration used when communicating with Ollama."""

    model: str = "mistral:7b-instruct"
    timeout: float | None = None


def load_prompt(prompt_path: Path | str) -> str:
    """Return the contents of a prompt file.

    Parameters
    ----------
    prompt_path:
        The path to the prompt template used when crafting requests.
    """

    path = Path(prompt_path)
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    return path.read_text(encoding="utf-8")


def chunk_log_file(log_path: Path | str, chunk_size: int = 50) -> Iterator[str]:
    """Yield newline-separated chunks from *log_path*.

    The file is streamed instead of being loaded entirely into memory, which
    keeps memory usage predictable even for multi-gigabyte log files.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        buffer: list[str] = []
        for line in handle:
            buffer.append(line.rstrip("\n"))
            if len(buffer) >= chunk_size:
                yield "\n".join(buffer)
                buffer.clear()
        if buffer:
            yield "\n".join(buffer)


@dataclass
class OllamaAnalyzer:
    """Small helper that keeps prompt state between chunk evaluations."""

    prompt_path: Path | str
    config: OllamaConfig = OllamaConfig()

    def __post_init__(self) -> None:
        self._prompt = load_prompt(self.prompt_path)

    def analyze_chunk(self, log_chunk: str) -> str:
        """Ask Ollama to analyze a single log chunk."""

        if not log_chunk.strip():
            return "[INFO] No log lines provided for analysis."

        command = ["ollama", "run", self.config.model]
        full_prompt = _compose_prompt(self._prompt, log_chunk)

        try:
            result = subprocess.run(
                command,
                input=full_prompt,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.config.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise OllamaError(
                "Ollama executable not found. Ensure Ollama is installed and available in PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise OllamaError(
                f"Ollama timed out after {self.config.timeout} seconds while analyzing a chunk."
            ) from exc

        if result.returncode != 0:
            raise OllamaError(result.stderr.strip() or "Unknown Ollama error")

        return result.stdout.strip()

    def analyze_log_file(self, log_path: Path | str, chunk_size: int = 50) -> Iterator[str]:
        """Analyze *log_path* in chunks and yield responses lazily."""

        for chunk in chunk_log_file(log_path, chunk_size=chunk_size):
            try:
                yield self.analyze_chunk(chunk)
            except OllamaError as exc:
                yield f"[ERROR] Failed to process chunk: {exc}"


def _compose_prompt(base_prompt: str, log_chunk: str) -> str:
    return f"{base_prompt}\n\n### TASK ###\nAnalyze the following logs:\n{log_chunk}\n"


@lru_cache(maxsize=8)
def _cached_analyzer(prompt_path: str, model: str) -> OllamaAnalyzer:
    return OllamaAnalyzer(prompt_path=prompt_path, config=OllamaConfig(model=model))


def analyze_logs_ollama_chunk(
    log_chunk: str,
    prompt_path: str,
    model: str = "mistral:7b-instruct",
) -> str:
    """Analyze a single log chunk using a cached :class:`OllamaAnalyzer`."""

    analyzer = _cached_analyzer(str(Path(prompt_path).resolve()), model)
    return analyzer.analyze_chunk(log_chunk)


def analyze_log_file(
    log_path: Path | str,
    prompt_path: Path | str,
    *,
    model: str = "mistral:7b-instruct",
    chunk_size: int = 50,
    timeout: float | None = None,
) -> Iterator[str]:
    """High-level convenience wrapper used by the CLI."""

    analyzer = OllamaAnalyzer(
        prompt_path=prompt_path,
        config=OllamaConfig(model=model, timeout=timeout),
    )
    return analyzer.analyze_log_file(log_path, chunk_size=chunk_size)
