# AI Travel Planner

Builds a sightseeing plan of 1–11 days for any city with Claude, using real places from
OpenStreetMap, then checks the plan in code against your budget, opening hours and
travel times between stops.

```
City name ─► Nominatim (geocode) ─► Overpass API ─► SQLite (cached per city) ─► filter by interests ─► Claude ─► validator ─► Streamlit UI
```

## Requirements

- Python 3.10+ (3.12 recommended). macOS's built-in Python 3.9 uses an outdated
  LibreSSL and cannot connect to the Overpass API — install one with `brew install python@3.12`.
- An Anthropic API key — https://console.anthropic.com/

## Setup (once)

```bash
cd AItravelplaner

# 1. Virtual environment + dependencies
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. API key: create a file named .env in the project root containing
#    ANTHROPIC_API_KEY=sk-ant-...
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env && chmod 600 .env   # then put your real key in it

# 3. (Optional) pre-download a city's places into data/places.db (~30 s each).
#    The web app also downloads cities on demand, so you can skip this.
python -m data.seed            # Katowice (default)
python -m data.seed Kraków
```

## Run the web app

```bash
source .venv/bin/activate
streamlit run app.py
```

Your browser opens at http://localhost:8501.

1. **Pick a city** at the top of the sidebar. Choose **Add another city…** and type
   any city name to download its places (~30 s the first time; cached afterwards).
   **Refresh** re-downloads the current city, **Remove** deletes it locally.
2. Pick the trip dates (up to 11 days), the daily hours, the **pace**
   (Relaxed 3–4 stops a day · Balanced 4–6 · Packed 6–8), the **budget per person for
   the whole trip** in the city's currency, and interests, then press **Plan trip**.
   Claude plans every day in one go (~30–40 s for 3 days), using the **weather forecast**
   (Open-Meteo, for days up to ~16 days ahead) — rainy/cold days get more indoor stops.

You get:

- a header with city, dates, pace and total cost vs budget, plus trip-wide warnings,
- a **day selector** — one tab per day with the forecast (* marks a day with something to check),
- for the selected day: a **large map with numbered pins** (left) and a **timeline**
  (right) with times, prices, walking/transit time between stops and reasons,
- **Swap** on every stop: pick one of ~4 nearby places of the same kind that are open
  at that time and not used elsewhere in the trip (instant, no AI call),
- **Open in Google Maps** — all of the day's stops pinned as a walking route,
- **PDF guide** — cover page plus one page per day with a route map and details.

Stop the server with `Ctrl+C`.

## Other entry points

| Command | What it does |
|---|---|
| `python main.py` | Terminal version of the planner (single day, interactive prompts) |
| `python -m data.seed [CITY]` | Download / refresh a city's places from OpenStreetMap |
| `python tests/evaluate.py` | Run the 20 test queries and score the plans (calls the API 20×) |

## Teaching the AI how to plan

The files in `planner/instructions/` are added to Claude's instructions on every
request — edit them to change how plans are built, no code changes needed:

| File | Covers |
|---|---|
| `01_day_structure.md` | Pacing, meal times, variety, routing within a day |
| `02_multi_day.md` | No repeats, one theme/area per day, spreading the budget |
| `03_data_caveats.md` | How to treat costs, missing opening hours, Monday closures |
| `04_weather.md` | How rain, cold and heat should shape a day |
| `cities/<city>.md` | Optional notes for one city (e.g. `cities/kraków.md`) |

Any new `*.md` file in that folder is picked up automatically (in filename order).
Restart Streamlit after editing.

## Project layout

```
app.py                  Streamlit entry point
ui/                     Sidebar, trip view (day strip), day view (map + timeline), PDF export
main.py                 CLI frontend
config.py               Model, default city, travel speeds, interest → category mapping
data/                   City search + cache, Overpass fetcher, weather, SQLite, seed script
planner/                Candidate filtering, prompts, Claude call, trip pipeline, swaps
planner/instructions/   Editable planning guidance for the AI (Markdown)
validator/              Budget / opening hours / travel-time checks
tests/                  Test queries and evaluation harness
```

## Notes & limitations

- **Prices:** the currency comes from the city's country. Claude estimates each stop's
  price per person from its knowledge of local prices — treat them as estimates.
- **Place types** downloaded: museums, galleries, landmarks, viewpoints, monuments,
  castles, notable churches, parks, gardens, beaches, marinas, zoos, aquariums, theme
  and water parks, theatres, cinemas, restaurants, cafés, bars and malls. Cities
  downloaded before a new type was added need **Refresh** to pick it up.
- **City search** is typo-tolerant (Photon, OpenStreetMap-based): "krakw" finds Kraków.
- **Travel time:** gaps up to 15 minutes shorter than the estimated travel time are
  not reported (straight-line distances are rough). Tunable in `config.py`
  (`TRAVEL_TOLERANCE_MIN`; pace presets in `PACES`).
- **Compact days:** each place gets an `area` label (1.5 km grid around the centre) so
  Claude can keep every day in one neighbourhood.
- OpenStreetMap sometimes lists one attraction twice under different names; a plan may
  occasionally include both.
- The search area is the city's boundary, capped at 10 km from the centre.
- Upgrading from the Katowice-only version: the old `data/katowice.db` is no longer
  used; places now live in `data/places.db`.

- Maps use OpenStreetMap tiles (in the app and the PDF); the Google Maps button needs no key.
- PDF fonts: DejaVu Sans (`assets/fonts/`, free licence in `assets/fonts/LICENSE`).

## API key security

- The key lives only in `.env`, which is gitignored (never committed) and readable
  only by your user (`chmod 600 .env`).
- `.streamlit/config.toml` binds the app to `localhost`, so other devices on your
  network can't open it and spend your API credit. If you ever deploy it publicly,
  add authentication and an Anthropic spend limit first.
- If the key is ever exposed, revoke it at https://console.anthropic.com/settings/keys
  and put a new one in `.env`.

## Troubleshooting

- **`SSLV3_ALERT_HANDSHAKE_FAILURE`** when seeding — your venv uses macOS's Python 3.9.
  Recreate it with Python 3.12 (see Requirements).
- **Overpass 502 / 504** — the main server is busy; the fetcher automatically falls
  back to mirror servers. If all fail, wait a minute and retry.
- **"No Anthropic API key found"** — check `.env` exists in the project root and
  restart Streamlit.
