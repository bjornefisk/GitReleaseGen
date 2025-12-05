"""Theme definitions for HelixCommit CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from rich.style import Style
from rich.theme import Theme as RichTheme


@dataclass
class Theme:
    """Theme configuration for the CLI."""
    
    name: str
    
    # Primary colors
    primary: str = "cyan"
    secondary: str = "magenta"
    accent: str = "yellow"
    
    # Status colors
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "blue"
    
    # Commit type colors
    feat_color: str = "green"
    fix_color: str = "red"
    docs_color: str = "blue"
    perf_color: str = "yellow"
    refactor_color: str = "cyan"
    test_color: str = "magenta"
    chore_color: str = "dim"
    breaking_color: str = "bold red"
    
    # UI element colors
    border_color: str = "bright_black"
    muted: str = "dim"
    highlight: str = "bold"
    
    # Text styles
    title_style: str = "bold"
    subtitle_style: str = "italic"
    
    # Panel styles
    panel_border: str = "rounded"
    
    # Custom style overrides
    styles: Dict[str, str] = field(default_factory=dict)
    
    def to_rich_theme(self) -> RichTheme:
        """Convert to a Rich Theme object."""
        base_styles = {
            "primary": self.primary,
            "secondary": self.secondary,
            "accent": self.accent,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "info": self.info,
            "feat": self.feat_color,
            "fix": self.fix_color,
            "docs": self.docs_color,
            "perf": self.perf_color,
            "refactor": self.refactor_color,
            "test": self.test_color,
            "chore": self.chore_color,
            "breaking": self.breaking_color,
            "border": self.border_color,
            "muted": self.muted,
            "highlight": self.highlight,
            "title": self.title_style,
            "subtitle": self.subtitle_style,
            # Commit-specific styles
            "commit.sha": f"bold {self.primary}",
            "commit.author": self.secondary,
            "commit.date": self.muted,
            "commit.subject": "default",
            "commit.scope": f"bold {self.accent}",
            # Changelog styles
            "changelog.version": f"bold {self.primary}",
            "changelog.date": self.muted,
            "changelog.section": f"bold {self.secondary}",
            # Diff styles
            "diff.added": "green",
            "diff.removed": "red",
            "diff.changed": "yellow",
            "diff.header": f"bold {self.info}",
            # Progress styles
            "progress.percentage": self.primary,
            "progress.description": "default",
            "progress.spinner": self.accent,
            # Panel styles
            "panel.title": f"bold {self.primary}",
            "panel.border": self.border_color,
        }
        
        # Merge with custom overrides
        base_styles.update(self.styles)
        
        return RichTheme(base_styles)


# Dark theme - vibrant colors on dark background
DARK_THEME = Theme(
    name="dark",
    primary="bright_cyan",
    secondary="bright_magenta",
    accent="bright_yellow",
    success="bright_green",
    warning="bright_yellow",
    error="bright_red",
    info="bright_blue",
    feat_color="bright_green",
    fix_color="bright_red",
    docs_color="bright_blue",
    perf_color="bright_yellow",
    refactor_color="bright_cyan",
    test_color="bright_magenta",
    chore_color="bright_black",
    breaking_color="bold bright_red",
    border_color="bright_black",
    muted="bright_black",
    highlight="bold white",
)

# Light theme - darker colors for light backgrounds
LIGHT_THEME = Theme(
    name="light",
    primary="dark_cyan",
    secondary="dark_magenta",
    accent="dark_orange",
    success="dark_green",
    warning="dark_orange",
    error="dark_red",
    info="dark_blue",
    feat_color="dark_green",
    fix_color="dark_red",
    docs_color="dark_blue",
    perf_color="dark_orange",
    refactor_color="dark_cyan",
    test_color="dark_magenta",
    chore_color="grey50",
    breaking_color="bold dark_red",
    border_color="grey50",
    muted="grey50",
    highlight="bold black",
    styles={
        "default": "black",
    }
)

# Global theme state
_current_theme: Theme = DARK_THEME


def get_theme() -> Theme:
    """Get the current theme."""
    return _current_theme


def set_theme(theme: Theme | str) -> None:
    """Set the current theme.
    
    Args:
        theme: Theme object or name ('dark', 'light', 'auto')
    """
    global _current_theme
    
    if isinstance(theme, Theme):
        _current_theme = theme
    elif theme == "dark":
        _current_theme = DARK_THEME
    elif theme == "light":
        _current_theme = LIGHT_THEME
    elif theme == "auto":
        # Try to detect terminal background
        # Default to dark if can't detect
        _current_theme = DARK_THEME
    else:
        raise ValueError(f"Unknown theme: {theme}")


def get_commit_type_style(commit_type: str) -> str:
    """Get the style for a commit type."""
    theme = get_theme()
    type_map = {
        "feat": theme.feat_color,
        "feature": theme.feat_color,
        "fix": theme.fix_color,
        "bugfix": theme.fix_color,
        "docs": theme.docs_color,
        "documentation": theme.docs_color,
        "perf": theme.perf_color,
        "performance": theme.perf_color,
        "refactor": theme.refactor_color,
        "test": theme.test_color,
        "tests": theme.test_color,
        "chore": theme.chore_color,
        "build": theme.chore_color,
        "ci": theme.chore_color,
        "style": theme.secondary,
        "revert": theme.warning,
        "breaking": theme.breaking_color,
    }
    return type_map.get(commit_type.lower(), "default")


__all__ = [
    "Theme",
    "DARK_THEME",
    "LIGHT_THEME",
    "get_theme",
    "set_theme",
    "get_commit_type_style",
]

