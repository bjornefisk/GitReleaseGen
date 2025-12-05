"""Table components for HelixCommit CLI."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Sequence

from rich.table import Table
from rich.text import Text

from .themes import get_theme, get_commit_type_style

if TYPE_CHECKING:
    from ..models import ChangeItem, Changelog, ChangelogSection, CommitInfo


def commits_table(
    commits: Sequence["CommitInfo"],
    *,
    show_author: bool = True,
    show_date: bool = True,
    show_type: bool = True,
    max_subject_length: int = 60,
    title: Optional[str] = None,
) -> Table:
    """Create a table of commits.
    
    Args:
        commits: List of commits to display
        show_author: Whether to show author column
        show_date: Whether to show date column
        show_type: Whether to show commit type
        max_subject_length: Maximum subject display length
        title: Optional table title
        
    Returns:
        Rich Table object
    """
    theme = get_theme()
    
    table = Table(
        title=title,
        show_header=True,
        header_style="bold",
        border_style="border",
        title_style="panel.title",
    )
    
    # Add columns
    table.add_column("SHA", style="commit.sha", width=8)
    if show_type:
        table.add_column("Type", style="default", width=10)
    table.add_column("Subject", style="default", no_wrap=False)
    if show_author:
        table.add_column("Author", style="commit.author", width=20)
    if show_date:
        table.add_column("Date", style="commit.date", width=12)
    
    # Add rows
    for commit in commits:
        row = [commit.short_sha()]
        
        if show_type:
            # Try to extract type from conventional commit
            commit_type = _extract_commit_type(commit.subject)
            if commit_type:
                type_text = Text(commit_type)
                type_text.stylize(get_commit_type_style(commit_type))
                row.append(type_text)
            else:
                row.append("-")
        
        # Subject (truncated)
        subject = commit.subject
        if len(subject) > max_subject_length:
            subject = subject[:max_subject_length - 3] + "..."
        row.append(subject)
        
        if show_author:
            author = commit.author_name
            if len(author) > 18:
                author = author[:15] + "..."
            row.append(author)
        
        if show_date:
            row.append(commit.authored_date.strftime("%Y-%m-%d"))
        
        table.add_row(*row)
    
    return table


def changelog_table(
    changelog: "Changelog",
    *,
    show_details: bool = False,
    group_by_section: bool = True,
) -> Table:
    """Create a table representation of a changelog.
    
    Args:
        changelog: The changelog to display
        show_details: Whether to show item details
        group_by_section: Whether to group by section with headers
        
    Returns:
        Rich Table object
    """
    title = "Changelog"
    if changelog.version:
        title = f"Changelog - {changelog.version}"
    if changelog.date:
        title += f" ({changelog.date.strftime('%Y-%m-%d')})"
    
    table = Table(
        title=title,
        show_header=True,
        header_style="bold",
        border_style="border",
        title_style="panel.title",
    )
    
    table.add_column("Type", style="default", width=12)
    table.add_column("Scope", style="commit.scope", width=15)
    table.add_column("Description", style="default", no_wrap=False)
    if show_details:
        table.add_column("Details", style="muted", width=30)
    
    for section in changelog.sections:
        if not section.items:
            continue
        
        if group_by_section:
            # Add section header row
            table.add_row(
                Text(section.title, style="changelog.section"),
                "",
                "",
                "" if show_details else None,
            )
        
        for item in section.items:
            type_text = Text(item.type)
            type_text.stylize(get_commit_type_style(item.type))
            
            title_text = Text(item.title)
            if item.breaking:
                title_text.append(" ⚠️ BREAKING", style="breaking")
            
            row = [
                type_text,
                item.scope or "-",
                title_text,
            ]
            
            if show_details:
                details = (item.details or "")[:50]
                if item.details and len(item.details) > 50:
                    details += "..."
                row.append(details)
            
            table.add_row(*row)
    
    return table


def search_results_table(
    commits: Sequence["CommitInfo"],
    *,
    query: str = "",
    highlight_matches: bool = True,
) -> Table:
    """Create a table for search results.
    
    Args:
        commits: Matching commits
        query: Search query (for highlighting)
        highlight_matches: Whether to highlight query matches
        
    Returns:
        Rich Table object
    """
    title = f"Search Results ({len(commits)} matches)"
    if query:
        title = f"Search: '{query}' ({len(commits)} matches)"
    
    table = Table(
        title=title,
        show_header=True,
        header_style="bold",
        border_style="border",
        title_style="panel.title",
    )
    
    table.add_column("SHA", style="commit.sha", width=8)
    table.add_column("Type", width=10)
    table.add_column("Subject", no_wrap=False)
    table.add_column("Author", style="commit.author", width=20)
    table.add_column("Date", style="commit.date", width=12)
    
    for commit in commits:
        sha = commit.short_sha()
        commit_type = _extract_commit_type(commit.subject) or "-"
        subject = commit.subject
        author = commit.author_name
        date = commit.authored_date.strftime("%Y-%m-%d")
        
        # Highlight matches
        if highlight_matches and query:
            subject_text = _highlight_text(subject, query)
            author_text = _highlight_text(author, query)
        else:
            subject_text = subject
            author_text = author
        
        type_text = Text(commit_type)
        if commit_type != "-":
            type_text.stylize(get_commit_type_style(commit_type))
        
        table.add_row(sha, type_text, subject_text, author_text, date)
    
    return table


def summary_table(
    stats: dict,
    *,
    title: str = "Summary",
) -> Table:
    """Create a summary statistics table.
    
    Args:
        stats: Dictionary of stat name -> value
        title: Table title
        
    Returns:
        Rich Table object
    """
    table = Table(
        title=title,
        show_header=False,
        border_style="border",
        title_style="panel.title",
        box=None,
    )
    
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="primary")
    
    for key, value in stats.items():
        table.add_row(key, str(value))
    
    return table


def _extract_commit_type(subject: str) -> Optional[str]:
    """Extract commit type from a conventional commit subject."""
    import re
    match = re.match(r"^(\w+)(?:\([^)]+\))?[!:]", subject)
    if match:
        return match.group(1).lower()
    return None


def _highlight_text(text: str, query: str) -> Text:
    """Highlight query matches in text."""
    result = Text()
    query_lower = query.lower()
    text_lower = text.lower()
    
    start = 0
    while True:
        pos = text_lower.find(query_lower, start)
        if pos == -1:
            result.append(text[start:])
            break
        
        # Add text before match
        result.append(text[start:pos])
        # Add highlighted match
        result.append(text[pos:pos + len(query)], style="bold yellow reverse")
        start = pos + len(query)
    
    return result


__all__ = [
    "commits_table",
    "changelog_table",
    "search_results_table",
    "summary_table",
]

