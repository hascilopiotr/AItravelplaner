"""
Run once to populate the SQLite database from Overpass API.
Usage: python -m data.seed
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.db import init_db, upsert_place, count_places
from data.osm_fetcher import fetch_and_parse
from rich.console import Console
from rich.progress import track

console = Console()


def seed():
    console.print("[bold cyan]Initialising database...[/]")
    init_db()

    console.print("[bold cyan]Fetching Katowice attractions from Overpass API...[/]")
    places = fetch_and_parse()
    console.print(f"Found [bold]{len(places)}[/] places with names")

    for place in track(places, description="Saving to DB..."):
        upsert_place(place)

    console.print(f"[bold green]Done. Database has {count_places()} places.[/]")


if __name__ == "__main__":
    seed()
