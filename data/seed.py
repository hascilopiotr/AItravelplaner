"""
Download (or refresh) a city's places from OpenStreetMap into SQLite.
Usage: python -m data.seed [CITY]        (default: Katowice)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console

from config import DEFAULT_CITY
from data.cities import ensure_city
from data.db import count_places

console = Console()


def seed(city: str = DEFAULT_CITY):
    console.print(f"[bold cyan]Fetching places for {city} from OpenStreetMap...[/]")
    record = ensure_city(city, refresh=True)
    console.print(f"[bold green]Done. {record['display_name']}: "
                  f"{count_places(record['name'])} places.[/]")


if __name__ == "__main__":
    seed(" ".join(sys.argv[1:]) or DEFAULT_CITY)
