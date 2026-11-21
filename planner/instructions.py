"""
Loads the editable planning guidance in planner/instructions/ into the system prompt.

- Every *.md file directly in planner/instructions/ is included, in filename order.
- planner/instructions/cities/<city_key>.md is included only for that city.
"""

from __future__ import annotations

import os

INSTRUCTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instructions")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def load_instructions(city_key: str | None = None) -> str:
    parts = []
    if os.path.isdir(INSTRUCTIONS_DIR):
        for name in sorted(os.listdir(INSTRUCTIONS_DIR)):
            path = os.path.join(INSTRUCTIONS_DIR, name)
            if name.endswith(".md") and os.path.isfile(path):
                parts.append(_read(path))
    if city_key:
        city_file = os.path.join(INSTRUCTIONS_DIR, "cities", f"{city_key.strip().lower()}.md")
        if os.path.isfile(city_file):
            parts.append(f"# Notes for this city\n\n{_read(city_file)}")
    return "\n\n".join(p for p in parts if p)
