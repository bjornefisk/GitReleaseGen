"""YAML formatter for changelog output."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from ..models import ChangeItem, Changelog, ChangelogSection


def render_yaml(changelog: Changelog, *, default_flow_style: bool = False) -> str:
    """Render a changelog to YAML.

    Args:
        changelog: The changelog object to render.
        default_flow_style: If True, use flow style for collections (default: False).

    Returns:
        YAML string representation of the changelog.
    """
    data = _changelog_to_dict(changelog)
    return yaml.dump(
        data,
        default_flow_style=default_flow_style,
        allow_unicode=True,
        sort_keys=False,
    )


def _changelog_to_dict(changelog: Changelog) -> Dict[str, Any]:
    """Convert a Changelog object to a dictionary."""
    return {
        "version": changelog.version,
        "date": _format_datetime(changelog.date),
        "sections": [_section_to_dict(section) for section in changelog.sections],
        "metadata": changelog.metadata or {},
    }


def _section_to_dict(section: ChangelogSection) -> Dict[str, Any]:
    """Convert a ChangelogSection object to a dictionary."""
    return {
        "title": section.title,
        "items": [_item_to_dict(item) for item in section.items],
    }


def _item_to_dict(item: ChangeItem) -> Dict[str, Any]:
    """Convert a ChangeItem object to a dictionary."""
    return {
        "title": item.title,
        "type": item.type,
        "scope": item.scope,
        "breaking": item.breaking,
        "summary": item.summary,
        "details": item.details,
        "notes": item.notes,
        "references": item.references,
        "metadata": item.metadata or {},
    }


def _format_datetime(value: Optional[datetime]) -> Optional[str]:
    """Format a datetime as ISO 8601 string."""
    if value is None:
        return None
    return value.isoformat()


__all__ = ["render_yaml"]

