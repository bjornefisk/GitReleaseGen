"""Progress indicators and spinners for HelixCommit CLI."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterator, Optional, TypeVar

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.console import Group

from .console import get_console
from .themes import get_theme

T = TypeVar("T")


class TaskProgress:
    """Context manager for tracking progress of multiple tasks."""
    
    def __init__(
        self,
        description: str = "Processing...",
        total: Optional[int] = None,
        show_speed: bool = True,
    ):
        """Initialize the progress tracker.
        
        Args:
            description: Description of the overall task
            total: Total number of items (None for indeterminate)
            show_speed: Whether to show processing speed
        """
        self.description = description
        self.total = total
        self.show_speed = show_speed
        self._progress: Optional[Progress] = None
        self._task_id: Optional[int] = None
    
    def __enter__(self) -> "TaskProgress":
        columns = [
            SpinnerColumn(style="progress.spinner"),
            TextColumn("[progress.description]{task.description}"),
        ]
        
        if self.total is not None:
            columns.extend([
                BarColumn(),
                TaskProgressColumn(),
            ])
        
        columns.append(TimeElapsedColumn())
        
        self._progress = Progress(
            *columns,
            console=get_console(),
            transient=True,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(
            self.description,
            total=self.total,
        )
        return self
    
    def __exit__(self, *args) -> None:
        if self._progress:
            self._progress.stop()
    
    def update(
        self,
        advance: int = 1,
        description: Optional[str] = None,
    ) -> None:
        """Update progress.
        
        Args:
            advance: Amount to advance by
            description: Optional new description
        """
        if self._progress and self._task_id is not None:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self._progress.update(self._task_id, **kwargs)
    
    def set_total(self, total: int) -> None:
        """Set the total count.
        
        Args:
            total: New total count
        """
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, total=total)


@contextmanager
def ai_spinner(
    message: str = "Generating AI summary...",
    success_message: Optional[str] = None,
) -> Generator[None, None, None]:
    """Context manager for AI operation spinner.
    
    Args:
        message: Message to display during operation
        success_message: Optional message to show on completion
        
    Yields:
        None
    """
    console = get_console()
    theme = get_theme()
    
    with console.status(
        f"[progress.spinner]{message}[/]",
        spinner="dots",
    ):
        try:
            yield
        finally:
            pass
    
    if success_message:
        console.print(f"[success]✓[/] {success_message}")


@contextmanager
def progress_spinner(
    message: str = "Processing...",
    success_message: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Generator[None, None, None]:
    """Context manager for a simple spinner.
    
    Args:
        message: Message to display during operation
        success_message: Optional message to show on completion
        error_message: Optional message to show on error
        
    Yields:
        None
    """
    console = get_console()
    
    with console.status(f"[progress.spinner]{message}[/]", spinner="dots"):
        try:
            yield
            if success_message:
                console.print(f"[success]✓[/] {success_message}")
        except Exception:
            if error_message:
                console.print(f"[error]✗[/] {error_message}")
            raise


def iterate_with_progress(
    items: Iterator[T],
    total: Optional[int] = None,
    description: str = "Processing...",
) -> Iterator[T]:
    """Iterate over items with a progress bar.
    
    Args:
        items: Iterator of items
        total: Total count (if known)
        description: Progress description
        
    Yields:
        Items from the iterator
    """
    with TaskProgress(description=description, total=total) as progress:
        for item in items:
            yield item
            progress.update()


class StreamingOutput:
    """Helper for streaming AI output character by character."""
    
    def __init__(
        self,
        title: str = "AI Response",
        show_cursor: bool = True,
    ):
        """Initialize streaming output.
        
        Args:
            title: Title for the output panel
            show_cursor: Whether to show a cursor
        """
        self.title = title
        self.show_cursor = show_cursor
        self._console = get_console()
        self._buffer = ""
        self._live: Optional[Live] = None
    
    def __enter__(self) -> "StreamingOutput":
        self._live = Live(
            Text("▌", style="primary") if self.show_cursor else Text(""),
            console=self._console,
            refresh_per_second=30,
            transient=False,
        )
        self._live.start()
        return self
    
    def __exit__(self, *args) -> None:
        if self._live:
            # Show final content without cursor
            self._live.update(Text(self._buffer))
            self._live.stop()
    
    def write(self, text: str) -> None:
        """Write text to the streaming output.
        
        Args:
            text: Text to append
        """
        self._buffer += text
        if self._live:
            display = Text(self._buffer)
            if self.show_cursor:
                display.append("▌", style="primary")
            self._live.update(display)
    
    def write_line(self, text: str) -> None:
        """Write a line to the streaming output.
        
        Args:
            text: Line to append
        """
        self.write(text + "\n")


__all__ = [
    "TaskProgress",
    "ai_spinner",
    "progress_spinner",
    "iterate_with_progress",
    "StreamingOutput",
]

