"""Styled panels for HelixCommit CLI."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from rich.box import ROUNDED, HEAVY, DOUBLE
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown

from .console import get_console
from .themes import get_theme, get_commit_type_style

if TYPE_CHECKING:
    from ..models import ChangeItem, Changelog, ChangelogSection, CommitInfo


def commit_panel(
    commit: "CommitInfo",
    *,
    show_diff: bool = False,
    show_body: bool = True,
    expanded: bool = False,
) -> Panel:
    """Create a styled panel for a commit.
    
    Args:
        commit: The commit to display
        show_diff: Whether to include the diff
        show_body: Whether to include the commit body
        expanded: Whether to show full details
        
    Returns:
        Rich Panel object
    """
    theme = get_theme()
    
    # Build the content
    content = Text()
    
    # SHA and author line
    content.append(commit.short_sha(), style="commit.sha")
    content.append(" by ", style="muted")
    content.append(commit.author_name, style="commit.author")
    content.append(" on ", style="muted")
    content.append(
        commit.authored_date.strftime("%Y-%m-%d %H:%M"),
        style="commit.date"
    )
    content.append("\n\n")
    
    # Subject
    content.append(commit.subject, style="bold")
    
    # Body
    if show_body and commit.body:
        content.append("\n\n")
        content.append(commit.body, style="default")
    
    # Diff
    if show_diff and commit.diff:
        content.append("\n\n")
        content.append("─" * 40, style="muted")
        content.append("\n")
        # Add syntax highlighted diff
        diff_syntax = Syntax(
            commit.diff[:2000] + ("..." if len(commit.diff) > 2000 else ""),
            "diff",
            theme="monokai",
            line_numbers=False,
        )
        # We'll need to return a Group for this case
        from rich.console import Group
        return Panel(
            Group(content, diff_syntax),
            title=f"[commit.sha]{commit.short_sha()}[/]",
            border_style="border",
            box=ROUNDED,
            expand=expanded,
        )
    
    return Panel(
        content,
        title=f"[commit.sha]{commit.short_sha()}[/]",
        border_style="border",
        box=ROUNDED,
        expand=expanded,
    )


def changelog_panel(
    changelog: "Changelog",
    *,
    show_metadata: bool = True,
) -> Panel:
    """Create a styled panel for a changelog.
    
    Args:
        changelog: The changelog to display
        show_metadata: Whether to show metadata
        
    Returns:
        Rich Panel object
    """
    from rich.console import Group
    
    content_parts = []
    
    # Version and date header
    header = Text()
    if changelog.version:
        header.append(changelog.version, style="changelog.version")
    if changelog.date:
        if changelog.version:
            header.append(" - ", style="muted")
        header.append(
            changelog.date.strftime("%Y-%m-%d"),
            style="changelog.date"
        )
    
    if header:
        content_parts.append(header)
        content_parts.append(Text())
    
    # Sections
    for section in changelog.sections:
        if not section.items:
            continue
            
        section_text = Text()
        section_text.append(f"\n{section.title}\n", style="changelog.section")
        
        for item in section.items:
            type_style = get_commit_type_style(item.type)
            section_text.append("  • ", style="muted")
            if item.scope:
                section_text.append(f"[{item.scope}] ", style="commit.scope")
            section_text.append(item.title)
            if item.breaking:
                section_text.append(" ⚠️ BREAKING", style="breaking")
            section_text.append("\n")
        
        content_parts.append(section_text)
    
    # Metadata
    if show_metadata and changelog.metadata:
        meta_text = Text("\n")
        meta_text.append("─" * 40, style="muted")
        meta_text.append("\n")
        for key, value in changelog.metadata.items():
            meta_text.append(f"{key}: ", style="muted")
            meta_text.append(str(value), style="info")
            meta_text.append("\n")
        content_parts.append(meta_text)
    
    title = "Changelog"
    if changelog.version:
        title = f"Changelog - {changelog.version}"
    
    return Panel(
        Group(*content_parts),
        title=f"[panel.title]{title}[/]",
        border_style="border",
        box=ROUNDED,
    )


def diff_panel(
    diff: str,
    *,
    title: str = "Diff",
    max_lines: int = 50,
) -> Panel:
    """Create a syntax-highlighted diff panel.
    
    Args:
        diff: The diff content
        title: Panel title
        max_lines: Maximum lines to show
        
    Returns:
        Rich Panel object
    """
    lines = diff.split("\n")
    if len(lines) > max_lines:
        truncated = "\n".join(lines[:max_lines])
        truncated += f"\n\n... ({len(lines) - max_lines} more lines)"
    else:
        truncated = diff
    
    syntax = Syntax(
        truncated,
        "diff",
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
    )
    
    return Panel(
        syntax,
        title=f"[panel.title]{title}[/]",
        border_style="border",
        box=ROUNDED,
    )


def error_panel(
    message: str,
    *,
    title: str = "Error",
    hint: Optional[str] = None,
) -> Panel:
    """Create an error message panel.
    
    Args:
        message: Error message
        title: Panel title
        hint: Optional hint for resolution
        
    Returns:
        Rich Panel object
    """
    content = Text()
    content.append("✗ ", style="error")
    content.append(message)
    
    if hint:
        content.append("\n\n")
        content.append("💡 ", style="info")
        content.append(hint, style="muted")
    
    return Panel(
        content,
        title=f"[error]{title}[/]",
        border_style="error",
        box=HEAVY,
    )


def success_panel(
    message: str,
    *,
    title: str = "Success",
    details: Optional[str] = None,
) -> Panel:
    """Create a success message panel.
    
    Args:
        message: Success message
        title: Panel title
        details: Optional additional details
        
    Returns:
        Rich Panel object
    """
    content = Text()
    content.append("✓ ", style="success")
    content.append(message)
    
    if details:
        content.append("\n\n")
        content.append(details, style="muted")
    
    return Panel(
        content,
        title=f"[success]{title}[/]",
        border_style="success",
        box=ROUNDED,
    )


def warning_panel(
    message: str,
    *,
    title: str = "Warning",
) -> Panel:
    """Create a warning message panel.
    
    Args:
        message: Warning message
        title: Panel title
        
    Returns:
        Rich Panel object
    """
    content = Text()
    content.append("⚠ ", style="warning")
    content.append(message)
    
    return Panel(
        content,
        title=f"[warning]{title}[/]",
        border_style="warning",
        box=ROUNDED,
    )


def info_panel(
    message: str,
    *,
    title: str = "Info",
    markdown: bool = False,
) -> Panel:
    """Create an info message panel.
    
    Args:
        message: Info message
        title: Panel title
        markdown: Whether to render as markdown
        
    Returns:
        Rich Panel object
    """
    if markdown:
        content = Markdown(message)
    else:
        content = Text()
        content.append("ℹ ", style="info")
        content.append(message)
    
    return Panel(
        content,
        title=f"[info]{title}[/]",
        border_style="info",
        box=ROUNDED,
    )


def section_panel(
    section: "ChangelogSection",
    *,
    show_details: bool = False,
) -> Panel:
    """Create a panel for a changelog section.
    
    Args:
        section: The changelog section
        show_details: Whether to show item details
        
    Returns:
        Rich Panel object
    """
    content = Text()
    
    for i, item in enumerate(section.items):
        if i > 0:
            content.append("\n")
        
        type_style = get_commit_type_style(item.type)
        content.append("• ", style=type_style)
        
        if item.scope:
            content.append(f"[{item.scope}] ", style="commit.scope")
        
        content.append(item.title)
        
        if item.breaking:
            content.append(" ⚠️", style="breaking")
        
        if show_details and item.details:
            content.append("\n  ")
            content.append(item.details[:200], style="muted")
            if len(item.details) > 200:
                content.append("...", style="muted")
    
    return Panel(
        content,
        title=f"[changelog.section]{section.title}[/]",
        border_style="border",
        box=ROUNDED,
    )


__all__ = [
    "commit_panel",
    "changelog_panel",
    "diff_panel",
    "error_panel",
    "success_panel",
    "warning_panel",
    "info_panel",
    "section_panel",
]

