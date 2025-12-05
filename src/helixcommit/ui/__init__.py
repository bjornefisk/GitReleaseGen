"""Rich UI components for HelixCommit CLI."""

from .console import get_console, get_err_console, refresh_consoles
from .panels import (
    commit_panel,
    changelog_panel,
    diff_panel,
    error_panel,
    success_panel,
    warning_panel,
    info_panel,
)
from .tables import (
    commits_table,
    changelog_table,
    search_results_table,
)
from .spinners import (
    ai_spinner,
    progress_spinner,
    TaskProgress,
)
from .themes import (
    Theme,
    get_theme,
    set_theme,
    DARK_THEME,
    LIGHT_THEME,
)

__all__ = [
    # Console
    "get_console",
    "get_err_console",
    "refresh_consoles",
    # Panels
    "commit_panel",
    "changelog_panel",
    "diff_panel",
    "error_panel",
    "success_panel",
    "warning_panel",
    "info_panel",
    # Tables
    "commits_table",
    "changelog_table",
    "search_results_table",
    # Spinners
    "ai_spinner",
    "progress_spinner",
    "TaskProgress",
    # Themes
    "Theme",
    "get_theme",
    "set_theme",
    "DARK_THEME",
    "LIGHT_THEME",
]

