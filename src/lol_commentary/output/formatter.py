from __future__ import annotations
import json
import sys
import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .segment_context import CommentaryOutput, CommentaryEntry

logger = logging.getLogger(__name__)

# Significance thresholds for display
SIGNIFICANCE_COLORS = {
    0.8: "bold red",
    0.6: "bold yellow",
    0.4: "cyan",
    0.0: "dim white",
}

TYPE_LABELS = {
    "player": "[blue]PLAYER[/blue]",
    "team": "[green]TEAM[/green]",
    "overall": "[bold red]OVERALL[/bold red]",
}


class CommentaryFormatter:
    """Format commentary output for display and file output."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def to_json(self, output: CommentaryOutput, filepath: Path | None = None, indent: int = 2) -> str:
        """Export commentary as JSON."""
        data = output.to_dict()
        json_str = json.dumps(data, ensure_ascii=False, indent=indent)

        if filepath:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(json_str, encoding="utf-8")
            logger.info(f"Commentary saved to {filepath}")

        return json_str

    def display_rich(self, output: CommentaryOutput):
        """Display commentary in rich terminal format."""
        info = output.game_info
        self.console.print()

        if output.analysis_mode == "frame_based":
            # Frame-based analysis header
            panel_content = f"[bold]Video:[/bold] {output.video_title}\n"
            panel_content += f"[bold]Mode:[/bold] フレームベース分析\n"
            panel_content += f"[bold]Frames:[/bold] {len(output.frames)}フレーム抽出済み"
            self.console.print(Panel(
                panel_content,
                title="[bold yellow]LoL Commentary (Frame-Based)[/bold yellow]",
                border_style="yellow",
            ))
        else:
            # Riot API analysis header
            self.console.print(Panel(
                f"[bold]Match:[/bold] {info.match_id}\n"
                f"[bold]Patch:[/bold] {info.patch}  |  [bold]Duration:[/bold] {info.duration}\n"
                f"[bold]Blue:[/bold] {', '.join(info.blue_team)}\n"
                f"[bold]Red:[/bold] {', '.join(info.red_team)}\n"
                f"[bold]Winner:[/bold] {'ブルー' if info.winner == 'blue' else 'レッド'}",
                title="[bold cyan]LoL Commentary[/bold cyan]",
                border_style="cyan",
            ))

        # Draft analysis
        if info.draft_analysis:
            self.console.print(Panel(
                info.draft_analysis,
                title="[bold green]Draft Analysis[/bold green]",
                border_style="green",
            ))

        # Commentary entries
        self.console.print()
        for entry in output.commentary:
            self._display_entry(entry)

        self.console.print()
        self.console.print(f"[dim]Total commentary entries: {len(output.commentary)}[/dim]")

    def _display_entry(self, entry: CommentaryEntry):
        """Display a single commentary entry."""
        # Get color based on significance
        color = "dim white"
        for threshold, c in sorted(SIGNIFICANCE_COLORS.items(), reverse=True):
            if entry.significance >= threshold:
                color = c
                break

        type_label = TYPE_LABELS.get(entry.type, entry.type)

        self.console.print(
            f"[dim]{entry.video_time}[/dim] "
            f"({entry.game_time}) "
            f"{type_label} "
            f"[{color}]{entry.message}[/{color}]"
        )

    def display_summary(self, output: CommentaryOutput):
        """Display a brief summary of the commentary."""
        table = Table(title="Commentary Summary")
        table.add_column("Type", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Avg Significance", justify="right")

        for entry_type in ["player", "team", "overall"]:
            entries = [e for e in output.commentary if e.type == entry_type]
            if entries:
                avg_sig = sum(e.significance for e in entries) / len(entries)
                table.add_row(entry_type, str(len(entries)), f"{avg_sig:.2f}")

        if output.frames:
            table.add_row("frames", str(len(output.frames)), "-")

        self.console.print(table)
