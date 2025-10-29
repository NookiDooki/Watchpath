import importlib.util
import sys
from pathlib import Path


def _load_severity_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "src" / "watchpath" / "ui" / "severity.py"
    spec = importlib.util.spec_from_file_location("watchpath.ui.severity", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


severity = _load_severity_module()
coerce_score = severity.coerce_score


def test_coerce_score_handles_named_severity():
    assert coerce_score("Serene") == 0.0
    assert coerce_score("  Alarmed  ") == 0.85
