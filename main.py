"""
Interactive CLI entry point.
Usage: python main.py
"""

import json
from datetime import date, timedelta
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich.json import JSON

from planner.pipeline import run
from data.db import init_db, count_places
from config import INTERESTS_OPTIONS

console = Console()


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def ask_preferences() -> dict:
    console.print(Panel("[bold cyan]AI Travel Planner — Katowice[/]", expand=False))
    init_db()
    n = count_places()
    console.print(f"Database has [bold]{n}[/] places loaded.\n")
    if n == 0:
        console.print("[yellow]Warning: database is empty. Run 'python -m data.seed' first.[/]\n")

    budget = IntPrompt.ask("Your budget (PLN)", default=150)
    start_time = Prompt.ask("Start time (HH:MM)", default="10:00")
    end_time = Prompt.ask("End time (HH:MM)", default="19:00")

    console.print(f"Interests: {', '.join(INTERESTS_OPTIONS)}")
    interests_raw = Prompt.ask("Your interests (comma-separated)", default="museums, food, parks")
    interests = [i.strip() for i in interests_raw.split(",")]

    tomorrow = date.today() + timedelta(days=1)
    visit_date = Prompt.ask("Visit date (YYYY-MM-DD)", default=tomorrow.isoformat())
    day_of_week = DAYS[date.fromisoformat(visit_date).weekday()]
    console.print(f"  → {day_of_week}")

    notes = Prompt.ask("Any notes? (optional)", default="")

    return {
        "budget_pln": float(budget),
        "start_time": start_time,
        "end_time": end_time,
        "interests": interests,
        "day_of_week": day_of_week,
        "visit_date": visit_date,
        "notes": notes,
    }


def print_result(result: dict):
    plan = result["plan"]
    validation = result["validation"]

    console.print(f"\n[bold]Plan summary:[/] {plan.get('plan_summary', '')}\n")

    for i, stop in enumerate(plan.get("stops", []), 1):
        console.print(
            f"  [bold]{i}.[/] [cyan]{stop['name']}[/]  "
            f"{stop['arrival']} – {stop['departure']}  "
            f"[yellow]{stop['cost_pln']} PLN[/]"
        )
        console.print(f"     {stop.get('reason', '')}")

    console.print()
    if validation["ok"]:
        console.print("[bold green]✓ Plan validated — no issues found.[/]")
    else:
        console.print("[bold red]✗ Validation found issues:[/]")
        if not validation["budget_ok"]:
            console.print(
                f"  [red]Budget exceeded:[/] {validation['total_cost']:.0f} PLN "
                f"> {validation['budget_limit']:.0f} PLN"
            )
        for v in validation["hours_violations"]:
            console.print(f"  [red]Opening hours:[/] {v}")
        for v in validation["travel_violations"]:
            console.print(f"  [red]Travel time:[/] {v}")
        for v in validation["unknown_places"]:
            console.print(f"  [red]Unknown place:[/] {v}")


def main():
    prefs = ask_preferences()
    console.print("\n[dim]Generating plan...[/]")
    result = run(prefs)
    print_result(result)


if __name__ == "__main__":
    main()
