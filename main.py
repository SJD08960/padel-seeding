import argparse
import sys

from rich.console import Console
from rich.rule import Rule

from parser import parse_rankings, parse_signups
from algorithm import compute_seeding
from display import render_seeding, save_csv

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Generate seeding for the next padel tournament."
    )
    parser.add_argument(
        "rankings_csv",
        help="CSV file with historical tournament rankings (columns = tournaments, rows = players by rank)",
    )
    parser.add_argument(
        "signups_txt",
        help="Text file with one signed-up player name per line",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Optional: save results to a CSV file",
    )
    args = parser.parse_args()

    console.print(Rule("[bold cyan]Padel Tournament Seeder[/bold cyan]"))
    console.print()

    # --- Load rankings ---
    console.print(f"[dim]Loading rankings from:[/dim] [white]{args.rankings_csv}[/white]")
    try:
        rankings, tournaments, display_names = parse_rankings(args.rankings_csv)
    except Exception as e:
        console.print(f"[red]Error reading rankings CSV:[/red] {e}")
        sys.exit(1)

    all_players = set(p for t in rankings.values() for p in t)
    console.print(
        f"  [green]OK[/green] Found [bold]{len(tournaments)}[/bold] tournament(s) "
        f"spanning [bold]{tournaments[0]}[/bold] to [bold]{tournaments[-1]}[/bold], "
        f"[bold]{len(all_players)}[/bold] unique player(s)"
    )
    console.print()

    # --- Load signups ---
    console.print(f"[dim]Loading signups from:[/dim] [white]{args.signups_txt}[/white]")
    try:
        signups = parse_signups(args.signups_txt)
    except Exception as e:
        console.print(f"[red]Error reading signup file:[/red] {e}")
        sys.exit(1)

    if not signups:
        console.print("[red]Signup list is empty.[/red]")
        sys.exit(1)

    if not tournaments:
        console.print("[red]No tournaments found in rankings CSV.[/red]")
        sys.exit(1)

    console.print(f"  [green]OK[/green] [bold]{len(signups)}[/bold] player(s) signed up")
    console.print()

    # --- Run algorithm ---
    console.print(Rule("[dim]Computing seeding[/dim]"))
    console.print()
    seeding = compute_seeding(rankings, tournaments, display_names, signups, console=console)

    # --- Summary ---
    console.print()
    console.print(Rule("[dim]Result[/dim]"))
    most_recent = tournaments[-1]
    render_seeding(seeding, tournament_date=most_recent)

    if args.output:
        save_csv(seeding, args.output)


if __name__ == "__main__":
    main()
