"""
PDF trip guide: cover page + one page per day with a route map, timeline and details.
"""

from __future__ import annotations

import io
import os
from datetime import date

from fpdf import FPDF
from PIL import ImageDraw, ImageFont

from config import PACES
from data.db import get_place_by_id
from data.osm_fetcher import HEADERS
from data.weather import weather_text

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(_ROOT, "assets", "fonts", "DejaVuSans.ttf")
FONT_BOLD = os.path.join(_ROOT, "assets", "fonts", "DejaVuSans-Bold.ttf")

ACCENT = (138, 44, 28)
GREY = (110, 110, 110)


def _money(x: float, cur: str) -> str:
    return f"{x:,.0f} {cur}"


def route_map_png(points: list[tuple[float, float]], width: int = 1000, height: int = 520) -> bytes | None:
    """Static OpenStreetMap image with the route and numbered pins. None if tiles fail."""
    try:
        from staticmap import CircleMarker, Line, StaticMap
        from staticmap.staticmap import _lat_to_y, _lon_to_x

        m = StaticMap(width, height, padding_x=60, padding_y=60,
                      url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                      headers=HEADERS, tile_request_timeout=10)
        lonlat = [(lon, lat) for lat, lon in points]
        if len(lonlat) > 1:
            m.add_line(Line(lonlat, "#ffffff", 7))
            m.add_line(Line(lonlat, "#8a2c1c", 4))
        for p in lonlat:
            m.add_marker(CircleMarker(p, "#ffffff", 30))
            m.add_marker(CircleMarker(p, "#8a2c1c", 24))
        img = m.render(zoom=min(m._calculate_zoom(), 16) if len(lonlat) > 1 else 15)

        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(FONT_BOLD, 15)
        for i, (lon, lat) in enumerate(lonlat, 1):
            x = m._x_to_px(_lon_to_x(lon, m.zoom))
            y = m._y_to_px(_lat_to_y(lat, m.zoom))
            draw.text((x, y), str(i), fill="white", font=font, anchor="mm")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


class _Guide(FPDF):
    def __init__(self, title: str):
        super().__init__(format="A4")
        self.title_text = title
        self.add_font("DejaVu", "", FONT)
        self.add_font("DejaVu", "B", FONT_BOLD)
        self.set_auto_page_break(True, margin=15)
        self.set_margins(15, 15, 15)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, f"{self.title_text}  ·  page {self.page_no()}", align="C")

    def h1(self, text: str):
        self.set_font("DejaVu", "B", 20)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")

    def h2(self, text: str):
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")

    def body(self, text: str, size: int = 10, color=(40, 40, 40), bold: bool = False):
        self.set_font("DejaVu", "B" if bold else "", size)
        self.set_text_color(*color)
        self.multi_cell(0, size * 0.5 + 1, text, new_x="LMARGIN", new_y="NEXT")


def build_trip_pdf(result: dict, city_label: str) -> bytes:
    prefs, tv = result["prefs"], result["trip_validation"]
    cur = prefs["currency"]
    dates = prefs["dates"]
    d0, d1 = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    city = city_label.split(" — ")[0].split(",")[0]
    pdf = _Guide(f"{city} trip guide")

    # ── Cover ──
    pdf.add_page()
    pdf.ln(20)
    pdf.set_font("DejaVu", "B", 30)
    pdf.set_text_color(*ACCENT)
    pdf.multi_cell(0, 14, city, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 30, 30)
    pdf.h2(f"{len(dates)}-day trip · {d0.strftime('%d %b')} – {d1.strftime('%d %b %Y')}")
    pdf.body(city_label, color=GREY)
    pdf.ln(6)
    pace = PACES.get(prefs.get("pace"), {}).get("label", prefs.get("pace", ""))
    for k, v in [("Daily hours", f"{prefs['start_time']}–{prefs['end_time']}"),
                 ("Pace", pace),
                 ("Interests", ", ".join(prefs.get("interests", []))),
                 ("Budget", f"{_money(tv['total_cost'], cur)} planned of {_money(tv['budget_limit'], cur)}"
                            " per person")]:
        pdf.set_font("DejaVu", "B", 10)
        pdf.cell(32, 6, k)
        pdf.set_font("DejaVu", "", 10)
        pdf.multi_cell(0, 6, v, new_x="LMARGIN", new_y="NEXT")
    if prefs.get("notes"):
        pdf.body(f"Notes: {prefs['notes']}")
    pdf.ln(4)
    pdf.body(result["plan"].get("trip_summary", ""), size=11)
    pdf.ln(6)

    # Overview table
    pdf.h2("Overview")
    pdf.set_font("DejaVu", "", 9)
    with pdf.table(col_widths=(28, 22, 70, 14, 46), text_align=("LEFT", "LEFT", "LEFT", "RIGHT", "LEFT"),
                   line_height=5.5) as table:
        head = table.row()
        for h in ("Date", "Day", "Theme", "Stops", "Weather"):
            head.cell(h)
        for day in result["days"]:
            row = table.row()
            row.cell(date.fromisoformat(day["date"]).strftime("%d %b"))
            row.cell(day["day_of_week"])
            row.cell(day["plan"].get("summary", ""))
            row.cell(str(len(day["plan"].get("stops", []))))
            row.cell(weather_text(day.get("weather"), emoji=False))

    # ── Day pages ──
    for n, day in enumerate(result["days"], 1):
        stops = day["plan"].get("stops", [])
        places = [get_place_by_id(prefs["city"], s.get("place_id", "")) or {} for s in stops]
        pdf.add_page()
        d = date.fromisoformat(day["date"])
        pdf.h1(f"Day {n} · {day['day_of_week']} {d.strftime('%d %B %Y')}")
        pdf.body(f"Weather: {weather_text(day.get('weather'), emoji=False)}   ·   "
                 f"{len(stops)} stops   ·   {_money(day['validation']['total_cost'], cur)}", color=GREY)
        if day["plan"].get("summary"):
            pdf.ln(1)
            pdf.body(day["plan"]["summary"], size=11)
        pdf.ln(3)

        pts = [(p["lat"], p["lon"]) for p in places if p.get("lat") is not None]
        png = route_map_png(pts) if pts else None
        if png:
            pdf.image(io.BytesIO(png), w=pdf.epw)
            pdf.set_font("DejaVu", "", 6)
            pdf.set_text_color(*GREY)
            pdf.cell(0, 4, "Map data © OpenStreetMap contributors", align="R",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        for i, (s, p) in enumerate(zip(stops, places), 1):
            if pdf.will_page_break(22):
                pdf.add_page()
            pdf.set_fill_color(*ACCENT)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("DejaVu", "B", 10)
            pdf.cell(7, 7, str(i), align="C", fill=True)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(31, 7, f" {s.get('arrival', '')}–{s.get('departure', '')}")
            pdf.cell(pdf.epw - 7 - 31 - 25, 7, s.get("name", "?"))
            pdf.set_font("DejaVu", "", 10)
            pdf.cell(25, 7, _money(float(s.get("cost", 0) or 0), cur), align="R",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_x(pdf.l_margin + 7)
            pdf.set_font("DejaVu", "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(pdf.epw - 7, 4.6, s.get("reason", ""), new_x="LMARGIN", new_y="NEXT")
            meta = [x for x in (p.get("subcategory"), p.get("address"),
                                f"Hours: {p['opening_hours']}" if p.get("opening_hours") else None) if x]
            if meta:
                pdf.set_x(pdf.l_margin + 7)
                pdf.set_text_color(*GREY)
                pdf.set_font("DejaVu", "", 8)
                pdf.multi_cell(pdf.epw - 7, 4.2, " · ".join(meta), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        v = day["validation"]
        issues = v["hours_violations"] + v["travel_violations"] + \
            [f"Not in database: {x}" for x in v["unknown_places"]]
        if issues:
            pdf.ln(2)
            pdf.body("Check before you go:", bold=True, color=ACCENT)
            for x in issues:
                pdf.body(f"•  {x}", size=9)

    return bytes(pdf.output())
