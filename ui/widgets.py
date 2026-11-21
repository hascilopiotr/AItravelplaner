"""
Interactive pieces built with st.components.v2: they render straight into the page
(no iframe, natural height) and can send events back to Python.

Styling lives in ui/styles.css; behaviour in ui/js/*.js. Every JS module gets the
helpers from ui/js/_prelude.js prepended. Data from OSM / the AI is passed as JSON and
only ever inserted as text, never as HTML.
"""

from __future__ import annotations

import os

import streamlit as st

_JS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js")


def _js(name: str) -> str:
    with open(os.path.join(_JS_DIR, "_prelude.js"), encoding="utf-8") as f:
        prelude = f.read()
    with open(os.path.join(_JS_DIR, f"{name}.js"), encoding="utf-8") as f:
        return prelude + "\n" + f.read()


def _component(name: str):
    # isolate_styles=False: mount in the page DOM so ui/styles.css and Leaflet's CSS apply.
    return st.components.v2.component(f"tp_{name}", js=_js(name), isolate_styles=False)


_hero = _component("hero")
_day_strip = _component("day_strip")
_day_board = _component("day_board")
_welcome = _component("welcome")


def hero(data: dict):
    _hero(key="tp_hero", data=data)


def welcome(data: dict):
    _welcome(key="tp_welcome", data=data)


def day_strip(data: dict, on_pick) -> None:
    """Ticket row of days. `on_pick(iso)` runs before the rerun when a day is clicked."""
    def _cb():
        pick = (st.session_state.get("tp_days") or {}).get("pick")
        if pick:
            on_pick(pick)
    _day_strip(key="tp_days", data=data, on_pick_change=_cb)


def day_board(data: dict) -> int | None:
    """Itinerary + map for one day. Returns the stop index whose Swap was clicked."""
    res = _day_board(key="tp_day", data=data, on_swap_change=lambda: None)
    return getattr(res, "swap", None)
