"""UI widgets composing the Watchpath desktop experience."""

from .global_stats import GlobalStatsWidget
from .session_list import SessionListWidget
from .session_detail import SessionDetailWidget
from .prompt_manager import PromptManagerPanel

__all__ = [
    "GlobalStatsWidget",
    "SessionListWidget",
    "SessionDetailWidget",
    "PromptManagerPanel",
]
