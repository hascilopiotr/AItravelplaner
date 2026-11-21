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
