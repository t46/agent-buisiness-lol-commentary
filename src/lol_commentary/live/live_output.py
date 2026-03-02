from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .game_state import GameState

logger = logging.getLogger(__name__)

# Reuse significance colors from existing formatter
SIGNIFICANCE_COLORS = {
    0.8: "bold red",
    0.6: "bold yellow",
    0.4: "cyan",
    0.0: "dim white",
}


@dataclass
class CommentaryEntry:
    """A single live commentary entry."""
    game_time: str
    message: str
    significance: float


class LiveTerminalOutput:
    """Rich Live display for real-time LoL commentary."""

    MAX_ENTRIES = 20

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()
        self._live: Live | None = None
        self._state = GameState()
        self._entries: list[CommentaryEntry] = []

    def start(self) -> None:
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=2,
        )
        self._live.start()

    def update_state(self, state: GameState) -> None:
        self._state = state
        self._refresh()

    def add_commentary(self, entry: CommentaryEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries = self._entries[-self.MAX_ENTRIES:]
        self._refresh()

    def stop(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._render())

    def _render(self) -> Panel:
        # Header with score
        game_time = self._state.game_time or "--:--"
        score_line = f"  {game_time}  |  Blue {self._state.blue_score} - {self._state.red_score} Red"
        phase = {"early": "序盤", "mid": "中盤", "late": "終盤"}.get(
            self._state.game_phase, ""
        )
        if phase:
            score_line += f"  ({phase})"

        # Commentary entries
        lines: list[Text] = []
        for entry in reversed(self._entries):
            color = "dim white"
            for threshold, c in sorted(SIGNIFICANCE_COLORS.items(), reverse=True):
                if entry.significance >= threshold:
                    color = c
                    break
            line = Text()
            line.append(f"[{entry.game_time}] ", style="dim")
            line.append(entry.message, style=color)
            lines.append(line)

        # Build panel content
        content = Text()
        content.append(score_line + "\n", style="bold")
        content.append("─" * 50 + "\n", style="dim")
        for line in lines:
            content.append_text(line)
            content.append("\n")

        if not lines:
            content.append("配信を監視中...\n", style="dim italic")

        return Panel(
            content,
            title="[bold cyan]LoL Live Commentary[/bold cyan]",
            border_style="cyan",
        )

    def __enter__(self) -> LiveTerminalOutput:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


class TextFileOutput:
    """Write commentary to a text file (for OBS text source)."""

    MAX_LINES = 5

    def __init__(self, filepath: Path) -> None:
        self._filepath = filepath
        self._lines: list[str] = []
        # Ensure parent directory exists
        self._filepath.parent.mkdir(parents=True, exist_ok=True)

    def write(self, entry: CommentaryEntry) -> None:
        self._lines.append(f"[{entry.game_time}] {entry.message}")
        if len(self._lines) > self.MAX_LINES:
            self._lines = self._lines[-self.MAX_LINES:]
        self._filepath.write_text("\n".join(self._lines), encoding="utf-8")
