import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

DEFAULT_CITY = "Katowice"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "places.db")

WALKING_SPEED_KMH = 4.5
AVG_TRAM_SPEED_KMH = 20.0
WALK_MAX_KM = 1.5          # beyond this, assume public transport
TRANSIT_WAIT_MIN = 5       # waiting time added to every public-transport leg
TRAVEL_TOLERANCE_MIN = 15  # validator ignores travel gaps short by this much or less
AREA_GRID_KM = 1.5         # size of the neighbourhood grid used to keep days compact

# Interest options shown in the UI, mapped to place subcategories in the DB.
INTEREST_SUBCATEGORIES = {
    "museums": ["museum"],
    "galleries": ["gallery", "arts"],
    "monuments": ["monument", "memorial"],
    "history": ["historic", "monument", "memorial", "museum"],
    "architecture": ["landmark", "historic"],
    "parks": ["park", "garden"],
    "nature": ["park", "garden", "viewpoint"],
    "cafes": ["cafe"],
    "restaurants": ["restaurant"],
    "bars": ["bar"],
    "food": ["restaurant", "cafe", "fast_food"],
    "shopping": ["mall"],
    "theatre": ["theatre", "arts"],
    "cinema": ["cinema"],
}
INTERESTS_OPTIONS = list(INTEREST_SUBCATEGORIES)

# Trip pace presets: stops per day, minimum buffer (minutes) on top of travel time.
PACES = {
    "relaxed": {"label": "🐢 Relaxed", "stops": (3, 4), "buffer": 20,
                "note": "plenty of free time, a long unhurried lunch, no rushing"},
    "balanced": {"label": "🚶 Balanced", "stops": (4, 6), "buffer": 10,
                 "note": "a comfortable mix of sightseeing and breaks"},
    "packed": {"label": "🏃 Packed", "stops": (6, 8), "buffer": 5,
               "note": "see as much as possible, short breaks"},
}
DEFAULT_PACE = "balanced"
