"""
Evaluation harness.
Runs all test queries through two modes:
  - llm_only:  LLM output, no validation applied (but violations still counted)
  - validated: LLM output + validation (violations logged, plan summary shows issues)

Usage:
    python -m tests.evaluate [--mode llm_only|validated|both]

Outputs a summary table and saves results to tests/results.json.
"""

import sys
import json
import argparse
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.queries import TEST_QUERIES
from planner.pipeline import run
from rich.console import Console
from rich.table import Table

console = Console()
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")


def run_query(prefs: dict) -> dict:
    try:
        result = run(prefs)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "error": str(e), "plan": None, "validation": None}


def summarise(results: list[dict]) -> dict:
    total = len(results)
    errors = sum(1 for r in results if r["status"] == "error")
    ok_results = [r for r in results if r["status"] == "ok"]

    budget_violations = sum(
        1 for r in ok_results if r["validation"] and not r["validation"]["budget_ok"]
    )
    hours_violations = sum(
        1 for r in ok_results if r["validation"] and r["validation"]["hours_violations"]
    )
    travel_violations = sum(
        1 for r in ok_results if r["validation"] and r["validation"]["travel_violations"]
    )
    unknown_places = sum(
        1 for r in ok_results if r["validation"] and r["validation"]["unknown_places"]
    )
    any_violation = sum(
        1 for r in ok_results if r["validation"] and not r["validation"]["ok"]
    )

    return {
        "total": total,
        "errors": errors,
        "budget_violations": budget_violations,
        "hours_violations": hours_violations,
        "travel_violations": travel_violations,
        "unknown_places": unknown_places,
        "any_violation": any_violation,
        "violation_rate": f"{any_violation / max(total - errors, 1) * 100:.0f}%",
    }


def print_table(all_results: list[dict], queries: list[dict]):
    table = Table(title="Evaluation Results", show_lines=True)
    table.add_column("ID", style="dim")
    table.add_column("Label")
    table.add_column("Budget", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Budget OK", justify="center")
    table.add_column("Hours OK", justify="center")
    table.add_column("Travel OK", justify="center")
    table.add_column("Known places", justify="center")
    table.add_column("Status")

    for q, r in zip(queries, all_results):
        if r["status"] == "error":
            table.add_row(q["id"], q["label"], str(q["budget_pln"]),
                          "-", "-", "-", "-", "-", f"[red]ERROR: {r['error'][:40]}[/]")
            continue
        v = r["validation"]
        budget_ok = "[green]✓[/]" if v["budget_ok"] else "[red]✗[/]"
        hours_ok = "[green]✓[/]" if not v["hours_violations"] else "[red]✗[/]"
        travel_ok = "[green]✓[/]" if not v["travel_violations"] else "[red]✗[/]"
        known_ok = "[green]✓[/]" if not v["unknown_places"] else "[red]✗[/]"
        status = "[green]OK[/]" if v["ok"] else "[red]FAIL[/]"

        table.add_row(
            q["id"], q["label"],
            f"{q['budget_pln']} PLN", f"{v['total_cost']:.0f} PLN",
            budget_ok, hours_ok, travel_ok, known_ok, status,
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", nargs="*", help="Run only specific query IDs (e.g. q01 q03)")
    args = parser.parse_args()

    queries = TEST_QUERIES
    if args.queries:
        queries = [q for q in TEST_QUERIES if q["id"] in args.queries]

    console.print(f"[bold cyan]Running {len(queries)} queries...[/]")

    all_results = []
    for q in queries:
        console.print(f"  [{q['id']}] {q['label']}...", end=" ")
        r = run_query(q)
        all_results.append(r)
        status = "[green]ok[/]" if r["status"] == "ok" and r["validation"]["ok"] else "[red]FAIL[/]"
        console.print(status)

    print_table(all_results, queries)

    stats = summarise(all_results)
    console.print("\n[bold]Summary:[/]")
    for k, v in stats.items():
        console.print(f"  {k}: {v}")

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"queries": queries, "results": all_results, "summary": stats},
                  f, ensure_ascii=False, indent=2, default=str)
    console.print(f"\nResults saved to [cyan]{RESULTS_PATH}[/]")


if __name__ == "__main__":
    main()
