import csv as csv_module

from rich.console import Console
from rich.table import Table

console = Console()


def render_seeding(seeding: list[tuple[str, str]], tournament_date: str = "") -> None:
    title = "Seeding for Next Tournament"
    if tournament_date:
        title += f" (based on data up to {tournament_date})"

    table = Table(title=title, show_lines=True, header_style="bold cyan")
    table.add_column("Seed", style="bold white", justify="center", width=5)
    table.add_column("Player", style="bold green", min_width=20)
    table.add_column("Reason", style="dim white")

    for i, (player, reason) in enumerate(seeding, 1):
        table.add_row(str(i), player, reason)

    console.print()
    console.print(table)
    console.print()


def save_csv(seeding: list[tuple[str, str]], filepath: str) -> None:
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv_module.writer(f)
        writer.writerow(["Seed", "Player", "Reason"])
        for i, (player, reason) in enumerate(seeding, 1):
            writer.writerow([i, player, reason])
    console.print(f"[dim]Results saved to {filepath}[/dim]")
