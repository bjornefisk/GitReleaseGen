"""Shared Rich console instance with theme support."""

from __future__ import annotations

from typing import Optional

from rich.console import Console

from .themes import get_theme

# Main console for output
_console: Optional[Console] = None

# Error console for stderr
_err_console: Optional[Console] = None


def get_console(force_new: bool = False) -> Console:
    """Get the shared console instance.
    
    Args:
        force_new: Force creation of a new console (useful after theme change)
        
    Returns:
        The shared Rich Console instance
    """
    global _console
    
    if _console is None or force_new:
        theme = get_theme()
        _console = Console(
            theme=theme.to_rich_theme(),
            highlight=True,
            markup=True,
            emoji=True,
        )
    
    return _console


def get_err_console(force_new: bool = False) -> Console:
    """Get the shared error console instance.
    
    Args:
        force_new: Force creation of a new console
        
    Returns:
        The shared Rich Console for stderr
    """
    global _err_console
    
    if _err_console is None or force_new:
        theme = get_theme()
        _err_console = Console(
            stderr=True,
            theme=theme.to_rich_theme(),
            highlight=True,
            markup=True,
            emoji=True,
        )
    
    return _err_console


def refresh_consoles() -> None:
    """Refresh console instances with current theme."""
    global _console, _err_console
    _console = None
    _err_console = None
    get_console(force_new=True)
    get_err_console(force_new=True)


# Convenience access
console = property(lambda self: get_console())
err_console = property(lambda self: get_err_console())


__all__ = [
    "get_console",
    "get_err_console", 
    "refresh_consoles",
    "console",
    "err_console",
]

