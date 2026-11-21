# AI Travel Planner — Katowice

Builds a one-day sightseeing plan for Katowice with Claude, using real places from
OpenStreetMap, then checks the plan in code against your budget, opening hours and
travel times between stops.

```
OpenStreetMap (Overpass API) ─► SQLite ─► filter by interests ─► Claude ─► validator ─► Streamlit UI
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

# 2. API key
cp .env.example .env
#    then edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. Download Katowice places into data/katowice.db (~30 s)
python -m data.seed
```

## Run the web app

```bash
source .venv/bin/activate
streamlit run app.py
```

Your browser opens at http://localhost:8501. Pick a date, time window, budget and
interests in the sidebar and press **Generate plan**. You get:

- the itinerary with times, costs and why each stop was chosen,
- a map of the route,
- validation results (budget, opening hours, travel time, unknown places).

Stop the server with `Ctrl+C`.

## Other entry points

| Command | What it does |
|---|---|
| `python main.py` | Terminal version of the planner (interactive prompts) |
| `python -m data.seed` | Re-download / refresh places from OpenStreetMap |
| `python tests/evaluate.py` | Run the 20 test queries and score the plans (calls the API 20×) |

## Project layout

```
app.py                  Streamlit frontend
main.py                 CLI frontend
config.py               Model, city bbox, speeds, interest → category mapping
data/                   Overpass fetcher, SQLite access, seed script
planner/                Candidate filtering, prompts, Claude call, pipeline
validator/              Budget / opening hours / travel-time checks
tests/                  Test queries and evaluation harness
```

## Troubleshooting

- **`SSLV3_ALERT_HANDSHAKE_FAILURE`** when seeding — your venv uses macOS's Python 3.9.
  Recreate it with Python 3.12 (see Requirements).
- **Overpass 502 / 504** — the main server is busy; the fetcher automatically falls
  back to mirror servers. If all fail, wait a minute and retry.
- **"No Anthropic API key found"** — check `.env` exists in the project root and
  restart Streamlit.
