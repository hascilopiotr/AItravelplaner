import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

CITY = "Katowice"
CITY_BBOX = (50.1850, 18.9200, 50.3200, 19.1500)  # (lat_min, lon_min, lat_max, lon_max)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "katowice.db")

WALKING_SPEED_KMH = 4.5
AVG_TRAM_SPEED_KMH = 20.0

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
